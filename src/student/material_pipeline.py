"""
素材处理流水线
================

将 Student 阶段的素材处理显式拆分为：
1. 基础提取层：image / code / ref
2. 语义加工层：term / translator / tagger
3. 质量整理层：completeness / quality / publish_readiness

前两层通过 TaskDAG 调度，第三层在 DAG 完成后基于 Material 做规则化评估。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any

from src.core.material_store import Material
from src.core.task_engine import TaskDAG, TaskNode, TaskStatus
from src.core.worker import WorkerInput, WorkerOutput


@dataclass
class CompletenessChecker:
    min_content_chars: int = 80

    def evaluate(self, material: Material) -> Dict[str, Any]:
        missing = []
        if not (material.title or "").strip():
            missing.append("missing_title")
        if len((material.content or "").strip()) < self.min_content_chars:
            missing.append("content_too_short")
        if not material.tags:
            missing.append("missing_tags")
        if not material.terms:
            missing.append("missing_terms")

        return {
            "is_complete": not missing,
            "missing_fields": missing,
            "content_chars": len((material.content or "").strip()),
            "tag_count": len(material.tags or []),
            "term_count": len(material.terms or []),
            "reference_count": len(material.references or []),
            "image_count": len(material.images or []),
            "code_block_count": len(material.code_blocks or []),
        }


@dataclass
class QualityScorer:
    base_score: int = 100

    def evaluate(self, material: Material, completeness: Dict[str, Any]) -> Dict[str, Any]:
        score = self.base_score
        flags = []

        penalties = {
            "missing_title": 20,
            "content_too_short": 35,
            "missing_tags": 10,
            "missing_terms": 10,
        }
        for missing in completeness.get("missing_fields", []):
            score -= penalties.get(missing, 5)
            flags.append(missing)

        if not material.references:
            score -= 5
            flags.append("missing_references")
        if not material.images:
            flags.append("no_images")
        if not material.code_blocks:
            flags.append("no_code_blocks")
        if material.language not in ("", "zh", "mixed"):
            flags.append("non_chinese_content")
            score -= 10

        score = max(0, min(100, score))
        return {
            "score": score,
            "flags": list(dict.fromkeys(flags)),
            "grade": self._grade(score),
        }

    @staticmethod
    def _grade(score: int) -> str:
        if score >= 85:
            return "A"
        if score >= 70:
            return "B"
        if score >= 55:
            return "C"
        return "D"


@dataclass
class PublishReadinessMarker:
    min_score: int = 60

    def evaluate(self, material: Material, completeness: Dict[str, Any], quality: Dict[str, Any]) -> Dict[str, Any]:
        reasons = []
        reasons.extend(completeness.get("missing_fields", []))
        if quality.get("score", 0) < self.min_score:
            reasons.append("quality_score_below_threshold")

        return {
            "ready_for_publish": len(reasons) == 0,
            "reasons": list(dict.fromkeys(reasons)),
            "score_threshold": self.min_score,
        }


class MaterialProcessingPipeline:
    extraction_modules = ["image", "code", "ref"]
    semantic_modules = ["term", "translator", "tagger"]
    quality_modules = ["completeness", "quality", "publish_readiness"]

    def __init__(self, workers: Dict[str, Any], config: Dict[str, Any], image_save_dir: str):
        self.workers = workers
        self.config = config or {}
        self.image_save_dir = image_save_dir
        self.completeness_checker = CompletenessChecker()
        self.quality_scorer = QualityScorer()
        self.publish_readiness_marker = PublishReadinessMarker()

    def build_enrich_dag(self, material: Material, fetch_output: WorkerOutput) -> TaskDAG:
        dag = TaskDAG(name=f"enrich_{material.id}")
        node_ids: Dict[str, str] = {}
        student_cfg = self.config.get("student", {})

        if student_cfg.get("image_download", True) and self.workers.get("image"):
            img_node = TaskNode(
                name="image",
                worker=self.workers["image"],
                input_data=WorkerInput(
                    extra={
                        "images": fetch_output.data.get("images", []),
                        "save_dir": self.image_save_dir,
                        "interpret": student_cfg.get("image_interpret", True),
                    }
                ),
            )
            dag.add_node(img_node)
            node_ids["image"] = img_node.id

        code_node = TaskNode(
            name="code",
            worker=self.workers["code"],
            input_data=WorkerInput(content=material.content),
        )
        dag.add_node(code_node)
        node_ids["code"] = code_node.id

        term_node = TaskNode(
            name="term",
            worker=self.workers["term"],
            input_data=WorkerInput(content=material.content),
        )
        dag.add_node(term_node)
        node_ids["term"] = term_node.id

        ref_node = TaskNode(
            name="ref",
            worker=self.workers["ref"],
            input_data=WorkerInput(
                content=material.content,
                extra={"html": fetch_output.data.get("html", "")},
            ),
        )
        dag.add_node(ref_node)
        node_ids["ref"] = ref_node.id

        trans_node = TaskNode(
            name="translator",
            worker=self.workers["translator"],
            input_data=WorkerInput(content=material.content),
            depends_on=[node_ids["code"]],
        )
        dag.add_node(trans_node)
        node_ids["translator"] = trans_node.id

        trans_id = node_ids["translator"]

        def tagger_input_builder(upstream_outputs, current_input):
            trans_out = upstream_outputs.get(trans_id)
            if trans_out and trans_out.success and trans_out.data.get("translated"):
                content = trans_out.content
            else:
                content = current_input.content
            return WorkerInput(content=content, metadata=current_input.metadata)

        tag_node = TaskNode(
            name="tagger",
            worker=self.workers["tagger"],
            input_data=WorkerInput(content=material.content, metadata={"title": material.title}),
            depends_on=[node_ids["translator"]],
            input_builder=tagger_input_builder,
        )
        dag.add_node(tag_node)
        node_ids["tagger"] = tag_node.id

        return dag

    def apply_results(self, material: Material, dag: TaskDAG) -> Material:
        for node in dag.nodes.values():
            if node.status != TaskStatus.COMPLETED or not node.output or not node.output.success:
                continue
            if node.name == "image":
                material.images = node.output.data.get("images", [])
            elif node.name == "code":
                material.code_blocks = node.output.data.get("code_blocks", [])
            elif node.name == "term":
                material.terms = node.output.data.get("terms", [])
            elif node.name == "ref":
                material.references = node.output.data.get("references", [])
            elif node.name == "translator":
                if node.output.data.get("translated"):
                    material.content = node.output.content
                    material.language = "zh"
                else:
                    material.language = node.output.data.get("language", material.language or "zh")
            elif node.name == "tagger":
                material.tags = node.output.data.get("tags", [])

        completeness = self.completeness_checker.evaluate(material)
        quality = self.quality_scorer.evaluate(material, completeness)
        readiness = self.publish_readiness_marker.evaluate(material, completeness, quality)
        material.metadata.setdefault("processing", {})
        material.metadata["processing"].update(
            {
                "extraction_modules": self.extraction_modules,
                "semantic_modules": self.semantic_modules,
                "quality_modules": self.quality_modules,
                "completeness": completeness,
                "quality": quality,
                "ready_for_publish": readiness,
            }
        )
        return material
