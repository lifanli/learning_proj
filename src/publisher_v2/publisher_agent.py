"""
出版社智能体 (PublisherAgent)
==============================
主控：从素材库检索素材，规划书籍结构，逐章深度撰写，组装输出。
"""

import asyncio
import os
import re
from typing import Dict, List, Optional

import yaml

from src.core.material_store import MaterialStore
from src.core.progress import TaskCancellationRequested, raise_if_cancel_requested, report_progress
from src.core.worker import WorkerInput
from src.publisher_v2.book_planner import BookPlanner, BookOutline
from src.publisher_v2.workers.book_assembler import BookAssembler
from src.publisher_v2.workers.code_annotator import CodeAnnotator
from src.publisher_v2.workers.cross_referencer import CrossReferencer
from src.publisher_v2.workers.figure_integrator import FigureIntegrator
from src.publisher_v2.workers.material_retriever import MaterialRetriever
from src.publisher_v2.workers.outline_planner import OutlinePlanner
from src.publisher_v2.workers.quality_reviewer import QualityReviewer
from src.publisher_v2.workers.section_writer import SectionWriter
from src.utils.logger import logger


class PublisherAgent:
    """出版社智能体 - 主控"""

    def __init__(self):
        self.config = self._load_config()
        self.store = MaterialStore(self.config.get("paths", {}).get("materials", "data/materials"))
        self.kb_root = self.config.get("paths", {}).get("knowledge_base", "knowledge_base")

        self.planner = BookPlanner()
        self.retriever = MaterialRetriever()
        self.outline_planner = OutlinePlanner()
        self.writer = SectionWriter()
        self.code_annotator = CodeAnnotator()
        self.figure_integrator = FigureIntegrator()
        self.cross_referencer = CrossReferencer()
        self.reviewer = QualityReviewer()
        self.assembler = BookAssembler()

    def _load_config(self) -> dict:
        try:
            with open("config/settings.yaml", "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception:
            return {}

    def plan_book(self, topic: str, parent_id: str = None, tags: List[str] = None) -> BookOutline:
        logger.info(f"[PublisherAgent] 规划书籍: {topic}")
        outline = self.planner.plan_book(self.store, topic, parent_id, tags)
        logger.info(f"[PublisherAgent] 目录规划完成: {outline.title} | {len(outline.chapters)}章")
        return outline

    async def publish_book(
        self,
        topic: str,
        parent_id: str = None,
        tags: List[str] = None,
        output_dir: str = None,
    ) -> Dict:
        logger.info(f"[PublisherAgent] 开始出版: {topic}")
        report_progress(5, f"出版：开始规划 {topic}")
        raise_if_cancel_requested()

        outline = self.plan_book(topic, parent_id, tags)
        if not outline.chapters:
            report_progress(100, "出版：目录规划失败，无可用素材")
            return {"error": "目录规划失败，无可用素材", "status": "error"}
        report_progress(12, f"出版：目录规划完成，共 {len(outline.chapters)} 章")

        if not output_dir:
            output_dir = os.path.join(self.kb_root, self._make_dir_name(outline.title))

        pub_config = self.config.get("publisher", {})
        expected_sections = self._collect_expected_sections(outline)
        all_sections = [
            {"title": item["section"], "file_path": item["file_path"]}
            for item in expected_sections
        ]

        assembled_chapters = []
        missing_sections = []
        warnings = []
        max_concurrent_sections = pub_config.get("max_concurrent_sections", 3)

        for ch_idx, chapter in enumerate(outline.chapters):
            raise_if_cancel_requested()
            ch_title = chapter.get("title", f"第{ch_idx+1}章")
            logger.info(f"[PublisherAgent] 撰写章节 {ch_idx+1}/{len(outline.chapters)}: {ch_title}")
            chapter_start_progress = 15 + int(ch_idx / max(len(outline.chapters), 1) * 70)
            report_progress(
                chapter_start_progress,
                f"出版：撰写章节 {ch_idx + 1}/{len(outline.chapters)} - {ch_title}",
            )

            sections = chapter.get("sections", [])
            sem = asyncio.Semaphore(max_concurrent_sections)

            async def process_section(sec_idx, section):
                async with sem:
                    raise_if_cancel_requested()
                    return await self._process_section(ch_title, sec_idx, section, all_sections, pub_config)

            tasks = [process_section(sec_idx, section) for sec_idx, section in enumerate(sections)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            assembled_sections = []
            for sec_idx, result in enumerate(results):
                if isinstance(result, TaskCancellationRequested):
                    raise result
                section_title = sections[sec_idx].get("title", "")
                if isinstance(result, Exception):
                    reason = str(result)
                    logger.warning(f"节处理异常: {section_title}: {reason}")
                    missing_sections.append({"chapter": ch_title, "section": section_title, "reason": reason})
                    continue

                if not result or not result.get("content"):
                    reason = result.get("reason", "章节未生成") if isinstance(result, dict) else "章节未生成"
                    missing_sections.append({"chapter": ch_title, "section": section_title, "reason": reason})
                    continue

                assembled_sections.append(result)
                warnings.extend(result.get("warnings", []))

            assembled_chapters.append({"title": ch_title, "sections": assembled_sections})
            chapter_done_progress = 15 + int((ch_idx + 1) / max(len(outline.chapters), 1) * 70)
            report_progress(
                chapter_done_progress,
                f"出版：完成章节 {ch_idx + 1}/{len(outline.chapters)} - {ch_title}",
            )

        total_sections = sum(len(ch["sections"]) for ch in assembled_chapters)
        if total_sections == 0:
            report_progress(100, "出版：所有章节生成失败")
            return {
                "error": "所有章节生成失败，未输出书籍",
                "status": "error",
                "missing_sections": missing_sections,
                "warnings": warnings,
            }

        report = self._build_publish_report(
            outline=outline,
            assembled_chapters=assembled_chapters,
            expected_sections=expected_sections,
            missing_sections=missing_sections,
            warnings=warnings,
        )

        report_progress(90, "出版：组装知识库文件")
        output_path = self.assembler.assemble(
            output_dir=output_dir,
            book_title=outline.title,
            chapters=assembled_chapters,
            report=report,
        )

        report.update(
            {
                "output_dir": output_path,
                "title": outline.title,
                "chapters": len(assembled_chapters),
                "sections": total_sections,
                "files": total_sections + 2,
            }
        )
        logger.info(
            f"[PublisherAgent] 出版完成: {outline.title} | 状态={report['status']} | "
            f"{report['completed_sections']}/{report['expected_sections']}节"
        )
        report_progress(98, f"出版：完成 {report['completed_sections']}/{report['expected_sections']} 小节")
        return report

    async def _process_section(
        self,
        ch_title: str,
        sec_idx: int,
        section: dict,
        all_sections: list,
        pub_config: dict,
    ) -> Optional[Dict]:
        raise_if_cancel_requested()
        loop = asyncio.get_event_loop()
        sec_title = section.get("title", "")
        material_ids = section.get("material_ids", [])
        description = section.get("description", "")

        materials_data = self._retrieve_materials(material_ids)
        combined_content = self._combine_materials(materials_data)
        if not combined_content:
            logger.warning(f"章节 {sec_title} 无可用素材，跳过")
            return {"reason": "无可用素材"}

        content_type = self._detect_content_type(materials_data)
        all_images = []
        all_code = []
        all_source_urls = []
        for material in materials_data:
            all_images.extend(material.get("images", []))
            all_code.extend(material.get("code_blocks", []))
            if material.get("source_url"):
                all_source_urls.append(material["source_url"])

        max_context = pub_config.get("max_context_chars", 5000)
        outline_output = await loop.run_in_executor(
            None,
            self.outline_planner.run,
            WorkerInput(
                content=combined_content[:max_context],
                metadata={
                    "chapter_title": ch_title,
                    "section_title": sec_title,
                    "description": description,
                },
            ),
        )
        section_outline = outline_output.data.get("outline", [])

        write_output = await loop.run_in_executor(
            None,
            self.writer.run,
            WorkerInput(
                content=combined_content,
                metadata={"chapter_title": ch_title, "section_title": sec_title},
                extra={
                    "outline": section_outline,
                    "content_type": content_type,
                    "images": all_images,
                    "code_blocks": all_code,
                },
            ),
        )
        if not write_output.success:
            logger.warning(f"撰写失败 {sec_title}: {write_output.error}")
            return {"reason": f"撰写失败: {write_output.error}"}

        section_content = write_output.content
        worker_metrics = write_output.data or {}
        section_warnings = []

        if pub_config.get("include_code_annotations", True):
            code_output = await loop.run_in_executor(None, self.code_annotator.run, WorkerInput(content=section_content))
            if code_output.success:
                section_content = code_output.content
            else:
                section_warnings.append(f"{ch_title}/{sec_title}: 代码注释失败，保留原文")

        if pub_config.get("include_images", True) and all_images:
            fig_output = await loop.run_in_executor(
                None,
                self.figure_integrator.run,
                WorkerInput(content=section_content, extra={"images": all_images}),
            )
            if fig_output.success:
                section_content = fig_output.content
            else:
                section_warnings.append(f"{ch_title}/{sec_title}: 图片整合失败，保留正文")

        xref_output = await loop.run_in_executor(
            None,
            self.cross_referencer.run,
            WorkerInput(
                content=section_content,
                metadata={"section_title": sec_title},
                extra={
                    "all_sections": all_sections,
                    "source_urls": all_source_urls,
                    "source_materials": materials_data,
                },
            ),
        )
        if xref_output.success:
            section_content = xref_output.content
        else:
            section_warnings.append(f"{ch_title}/{sec_title}: 交叉引用失败")

        review_data = {}
        if pub_config.get("quality_review", True):
            review_output = await loop.run_in_executor(
                None,
                self.reviewer.run,
                WorkerInput(content=section_content, metadata={"section_title": sec_title}),
            )
            review_data = review_output.data or {}
            if not review_output.success:
                section_warnings.append(f"{ch_title}/{sec_title}: 质量审核失败")
            elif not review_data.get("passed", True):
                issues = review_data.get("issues", [])
                section_warnings.append(f"{ch_title}/{sec_title}: 质量审核未通过 - {'; '.join(issues[:3])}")

        quality = self._build_section_quality(section_content, worker_metrics, review_data)
        for flag in quality.get("flags", []):
            section_warnings.append(f"{ch_title}/{sec_title}: {flag}")

        logger.info(f"[PublisherAgent] 节 {sec_idx+1} 完成: {sec_title} ({len(section_content)}字)")
        return {
            "title": sec_title,
            "content": section_content,
            "quality": quality,
            "warnings": section_warnings,
        }

    async def publish_chapter(
        self,
        topic: str,
        chapter_index: int = 0,
        parent_id: str = None,
    ) -> Dict:
        outline = self.plan_book(topic, parent_id)
        if chapter_index >= len(outline.chapters):
            return {"error": f"章节索引 {chapter_index} 超出范围", "status": "error"}

        return await self.publish_book(topic=topic, parent_id=parent_id)

    def _retrieve_materials(self, material_ids: list) -> list:
        materials = []
        for mid in material_ids:
            mat = self.store.get(mid)
            if mat:
                materials.append(
                    {
                        "id": mat.id,
                        "title": mat.title,
                        "content": mat.content,
                        "source_type": mat.source_type,
                        "source_url": mat.source_url,
                        "images": mat.images,
                        "code_blocks": mat.code_blocks,
                        "references": mat.references,
                        "terms": mat.terms,
                        "tags": mat.tags,
                        "metadata": mat.metadata,
                    }
                )
        return materials

    @staticmethod
    def _combine_materials(materials: list) -> str:
        parts = []
        for mat in materials:
            content = (mat.get("content") or "").strip()
            if not content:
                continue
            provenance = PublisherAgent._format_material_provenance(mat)
            parts.append(
                "\n".join(
                    part for part in [
                        f"--- 素材: {mat.get('title', '') or mat.get('id', '未命名素材')} ---",
                        provenance,
                        "正文摘录:",
                        content,
                    ] if part
                )
            )
        return "\n\n".join(parts)

    @staticmethod
    def _format_material_provenance(material: dict) -> str:
        lines = []
        source_type = material.get("source_type") or "unknown"
        source_url = material.get("source_url") or ""
        references = material.get("references") or []

        lines.append(f"来源类型: {source_type}")
        if source_url:
            lines.append(f"来源链接: {source_url}")

        if references:
            lines.append("参考引用:")
            for ref in references[:8]:
                ref_title = ref.get("title") or ref.get("url") or "未命名引用"
                ref_type = ref.get("type") or "reference"
                ref_url = ref.get("url") or ""
                if ref_url:
                    lines.append(f"- [{ref_type}] {ref_title} - {ref_url}")
                else:
                    lines.append(f"- [{ref_type}] {ref_title}")

        return "\n".join(lines)

    @staticmethod
    def _detect_content_type(materials: list) -> str:
        source_types = {m.get("source_type", "") for m in materials}
        if "arxiv" in source_types:
            return "paper"
        if "github" in source_types:
            return "code"
        if "course_page" in source_types:
            return "tutorial"
        return "default"

    def _build_publish_report(
        self,
        outline: BookOutline,
        assembled_chapters: List[Dict],
        expected_sections: List[Dict],
        missing_sections: List[Dict],
        warnings: List[str],
    ) -> Dict:
        completed_sections = sum(len(ch["sections"]) for ch in assembled_chapters)
        expected_count = len(expected_sections)
        critical_flags = []
        quality_summary = []

        for chapter in assembled_chapters:
            for section in chapter.get("sections", []):
                quality = section.get("quality", {})
                flags = quality.get("flags", [])
                if flags:
                    quality_summary.append(
                        {
                            "chapter": chapter.get("title", ""),
                            "section": section.get("title", ""),
                            "flags": flags,
                        }
                    )
                    critical_flags.extend(flags)

        status = "success"
        if missing_sections or critical_flags:
            status = "partial"
        if completed_sections == 0:
            status = "error"

        return {
            "status": status,
            "expected_sections": expected_count,
            "completed_sections": completed_sections,
            "missing_sections": missing_sections,
            "warnings": warnings,
            "quality_summary": quality_summary,
            "outline_metadata": outline.metadata,
        }

    def _build_section_quality(self, content: str, worker_metrics: Dict, review_data: Dict) -> Dict:
        flags = list(worker_metrics.get("quality_flags", []))
        if review_data and not review_data.get("passed", True):
            flags.append("review_failed")
        flags = list(dict.fromkeys(flags))
        return {
            "chars": len(content),
            "estimated_length_units": worker_metrics.get("estimated_length_units", len(content)),
            "chunk_count": worker_metrics.get("chunk_count", 1),
            "flags": flags,
            "review_issues": review_data.get("issues", []),
            "review_suggestions": review_data.get("suggestions", []),
        }

    def _collect_expected_sections(self, outline: BookOutline) -> List[Dict]:
        expected = []
        for ch_idx, chapter in enumerate(outline.chapters):
            ch_title = chapter.get("title", f"第{ch_idx+1}章")
            ch_dir_name = self._safe_filename(ch_title)
            ch_dir_prefix = f"{ch_idx+1:02d}_{ch_dir_name}"
            for sec_idx, section in enumerate(chapter.get("sections", [])):
                sec_title = section.get("title", f"{ch_idx+1}.{sec_idx+1}")
                sec_filename = f"{sec_idx+1:02d}_{self._safe_filename(sec_title)}.md"
                expected.append(
                    {
                        "chapter": ch_title,
                        "section": sec_title,
                        "file_path": f"{ch_dir_prefix}/{sec_filename}",
                    }
                )
        return expected

    def _make_dir_name(self, title: str) -> str:
        max_idx = -1
        if os.path.exists(self.kb_root):
            for d in os.listdir(self.kb_root):
                match = re.match(r"^(\d+)_", d)
                if match:
                    max_idx = max(max_idx, int(match.group(1)))

        new_idx = max_idx + 1
        safe_title = re.sub(r'[<>:"/\\|?*]', '', title).strip().replace(" ", "_")[:30]
        return f"{new_idx:02d}_{safe_title}"

    @staticmethod
    def _safe_filename(title: str, max_len: int = 40) -> str:
        title = re.sub(r'^第?\d+[章节\.]\s*', '', title)
        safe = re.sub(r'[<>:"/\\|?*]', '', title)
        safe = safe.strip().replace(" ", "_")
        if len(safe) > max_len:
            safe = safe[:max_len]
        return safe or "untitled"
