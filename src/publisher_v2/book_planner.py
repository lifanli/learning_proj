"""
全书规划器 (BookPlanner)
=========================
从素材库检索素材，规划全书三级目录结构。
"""

import re
import yaml
import math
from collections import OrderedDict
from typing import List, Dict, Optional
from dataclasses import dataclass, field

from src.core.worker import BaseWorker, WorkerSpec, WorkerInput, WorkerOutput
from src.core.material_store import MaterialStore, Material
from src.utils.logger import logger


@dataclass
class BookOutline:
    """书籍目录结构"""
    title: str = ""
    description: str = ""
    chapters: List[Dict] = field(default_factory=list)
    # 每个chapter: {
    #   "title": str,
    #   "sections": [{"title": str, "material_ids": [str], "description": str}]
    # }
    metadata: Dict = field(default_factory=dict)


class BookPlanner(BaseWorker):
    """全书三级目录规划"""

    DEFAULT_FALLBACK_MAX_MATERIALS = 30
    DEFAULT_LONG_MATERIAL_CHARS = 120000
    DEFAULT_GROUP_LONG_MATERIAL_CHARS = 24000
    DEFAULT_MAX_SECTIONS_PER_CHAPTER = 10
    DEFAULT_SECTION_MATERIALS = 2

    def __init__(self):
        super().__init__(WorkerSpec(
            name="BookPlanner",
            description="基于素材库规划全书目录结构",
            model_level="deep",
            max_retries=2,
        ))

    def plan_book(self, store: MaterialStore, topic: str,
                  parent_id: str = None, tags: List[str] = None) -> BookOutline:
        """
        规划全书目录。

        Args:
            store: 素材库
            topic: 书籍主题
            parent_id: 限定某个父素材下的素材
            tags: 限定标签
        """
        # 检索相关素材
        materials = store.query(parent_id=parent_id, tags=tags, limit=200)
        if not materials:
            # 无parent_id限定，按关键词搜索
            materials = store.query(keyword=topic, limit=200)

        if not materials:
            logger.warning(f"未找到与 '{topic}' 相关的素材")
            return BookOutline(title=topic)

        materials = self._prioritize_materials(materials)

        # 准备素材摘要
        material_summaries = []
        priority_view = []
        for mat in materials:
            full_mat = store.get(mat.id) if hasattr(store, "get") and mat.id else None
            content_chars = len((full_mat.content if full_mat else mat.content) or "")
            summary = f"[{mat.source_type}] {mat.title}"
            if mat.tags:
                summary += f" | 标签: {', '.join(mat.tags)}"
            processing = (mat.metadata or {}).get("processing", {})
            quality = processing.get("quality", {}) if isinstance(processing, dict) else {}
            readiness = processing.get("ready_for_publish", {}) if isinstance(processing, dict) else {}
            score = quality.get("score") if isinstance(quality, dict) else None
            if score is not None:
                summary += f" | 质量:{score}"
            summary += " | 可出版" if readiness.get("ready_for_publish") else " | 待整理"
            if mat.summary:
                summary += f" | {mat.summary[:100]}"
            material_summaries.append({
                "id": mat.id,
                "summary": summary,
                "title": mat.title,
                "source_type": mat.source_type,
                "tags": list(mat.tags or []),
                "quality_score": score or 0,
                "ready_for_publish": bool(readiness.get("ready_for_publish")),
                "content_chars": content_chars,
            })
            priority_view.append(
                {
                    "id": mat.id,
                    "title": mat.title,
                    "quality_score": score or 0,
                    "ready_for_publish": bool(readiness.get("ready_for_publish")),
                    "content_chars": content_chars,
                }
            )

        # LLM规划目录
        outline = self._plan_with_llm(topic, material_summaries)
        outline.metadata.setdefault("material_priority", priority_view)

        return outline

    def _prioritize_materials(self, materials: List[Material]) -> List[Material]:
        def sort_key(mat: Material):
            processing = (mat.metadata or {}).get("processing", {})
            quality = processing.get("quality", {}) if isinstance(processing, dict) else {}
            readiness = processing.get("ready_for_publish", {}) if isinstance(processing, dict) else {}
            ready = 1 if readiness.get("ready_for_publish") else 0
            score = quality.get("score", 0) if isinstance(quality, dict) else 0
            return (-ready, -score, mat.order_index, -(mat.created_at or 0.0))

        return sorted(materials, key=sort_key)

    def _plan_with_llm(self, topic: str, material_summaries: list) -> BookOutline:
        """用LLM规划目录结构"""
        summaries_text = "\n".join(
            f"  [{ms['id']}] {ms['summary']}"
            for ms in material_summaries[:50]
        )

        prompt = f"""请为以下主题规划一本技术知识库的目录结构。

主题: {topic}

可用素材:
{summaries_text}

要求：
1. 设计3级目录结构：书名 → 章 → 节
2. 每章应覆盖一个完整的子主题
3. 每节对应一个或多个素材，标注素材ID
4. 章节按由浅入深的学习路径排列
5. 确保所有素材都被分配到某个章节

请严格按以下YAML格式输出：

```yaml
title: "书名"
description: "一句话描述"
chapters:
  - title: "第1章 章标题"
    sections:
      - title: "1.1 节标题"
        material_ids: ["id1", "id2"]
        description: "本节要点"
      - title: "1.2 节标题"
        material_ids: ["id3"]
        description: "本节要点"
  - title: "第2章 章标题"
    sections:
      - title: "2.1 节标题"
        material_ids: ["id4"]
        description: "本节要点"
```"""

        try:
            result = self.llm_call(
                prompt,
                system="你是技术书籍编辑，擅长设计清晰的知识体系。请严格按YAML格式输出目录结构。",
                enable_thinking=True,
            )

            outline = self._parse_outline(result)
            # 解析成功但无章节 → 降级
            if not outline.chapters:
                logger.warning("目录解析结果为空，使用降级方案")
                return self._fallback_outline(topic, material_summaries)
            return self._ensure_all_materials_assigned(outline, material_summaries)

        except Exception as e:
            logger.error(f"目录规划失败: {e}")
            # 降级：按素材顺序生成简单目录
            return self._fallback_outline(topic, material_summaries)

    def _parse_outline(self, llm_output: str) -> BookOutline:
        """解析LLM输出的YAML目录结构"""
        yaml_text = llm_output

        # 防御性清理：去除 <think> 标签（含未闭合情况）
        if "<think>" in yaml_text:
            # 先清除闭合标签对
            yaml_text = re.sub(r"<think>[\s\S]*?</think>", "", yaml_text)
            # 处理未闭合的 <think> 标签：保留 <think> 之前的内容
            if "<think>" in yaml_text:
                yaml_text = yaml_text.split("<think>")[0]
            yaml_text = yaml_text.strip()

        # 提取YAML块
        if "```yaml" in yaml_text:
            yaml_text = yaml_text.split("```yaml")[1].split("```")[0]
        elif "```" in yaml_text:
            yaml_text = yaml_text.split("```")[1].split("```")[0]

        try:
            data = yaml.safe_load(yaml_text)
            if not data:
                raise ValueError("空YAML")

            outline = BookOutline(
                title=data.get("title", ""),
                description=data.get("description", ""),
                chapters=data.get("chapters", []),
            )
            return outline
        except Exception as e:
            logger.warning(f"YAML解析失败: {e}")
            return BookOutline(title="未命名")

    def _fallback_outline(self, topic: str, summaries: list) -> BookOutline:
        """降级目录：确定性主题分组，避免退化成单章数百小节。"""
        max_materials = self._publisher_cfg().get(
            "fallback_max_materials",
            self.DEFAULT_FALLBACK_MAX_MATERIALS,
        )
        selected_summaries = summaries[:max_materials]
        deferred_summaries = summaries[max_materials:]
        outline = BookOutline(
            title=topic,
            description="自动按素材主题分组生成的出版目录",
            metadata={
                "fallback": True,
                "fallback_reason": "llm_planning_unavailable",
                "strategy": "deterministic_topic_grouping",
                "total_materials": len(summaries),
                "selected_materials": len(selected_summaries),
                "deferred_materials": [
                    {"id": ms.get("id"), "title": ms.get("title") or ms.get("summary", "")[:80]}
                    for ms in deferred_summaries
                ],
            },
        )
        outline.chapters = self._build_fallback_chapters(topic, selected_summaries, start_chapter=1)
        return outline

    def _ensure_all_materials_assigned(self, outline: BookOutline, summaries: list) -> BookOutline:
        """Ensure materials not visible to the LLM still appear in the final outline."""
        all_ids = {ms["id"] for ms in summaries}
        assigned = set()
        for chapter in outline.chapters:
            for section in chapter.get("sections", []):
                assigned.update(section.get("material_ids", []) or [])

        missing_ids = [ms["id"] for ms in summaries if ms["id"] in all_ids and ms["id"] not in assigned]
        if not missing_ids:
            outline.metadata["coverage"] = {"total_materials": len(all_ids), "assigned_materials": len(assigned)}
            return outline

        logger.warning(f"目录规划漏分配 {len(missing_ids)} 条素材，已自动按主题追加补齐章节")
        summary_by_id = {ms["id"]: ms["summary"] for ms in summaries}
        missing_summaries = [
            {**ms, "summary": summary_by_id.get(ms["id"], ms.get("summary", ms["id"]))}
            for ms in summaries
            if ms["id"] in missing_ids
        ]
        if len(missing_summaries) <= self._publisher_cfg().get("fallback_max_sections_per_chapter", self.DEFAULT_MAX_SECTIONS_PER_CHAPTER):
            appendix = {
                "title": "补充素材精读",
                "sections": self._build_sections_for_summaries(
                    missing_summaries,
                    chapter_index=len(outline.chapters) + 1,
                ),
            }
            outline.chapters.append(appendix)
        else:
            outline.chapters.extend(
                self._build_fallback_chapters(
                    "补充素材精读",
                    missing_summaries,
                    start_chapter=len(outline.chapters) + 1,
                )
            )
        outline.metadata["coverage"] = {
            "total_materials": len(all_ids),
            "assigned_materials": len(all_ids),
            "auto_assigned_materials": len(missing_ids),
            "auto_assignment_strategy": "deterministic_topic_grouping",
        }
        return outline

    def _build_fallback_chapters(self, topic: str, summaries: list, start_chapter: int = 1) -> List[Dict]:
        clusters = self._cluster_summaries(summaries)
        chapters = []
        chapter_index = start_chapter
        max_sections = self._publisher_cfg().get(
            "fallback_max_sections_per_chapter",
            self.DEFAULT_MAX_SECTIONS_PER_CHAPTER,
        )

        for label, items in clusters.items():
            section_items = self._expand_long_materials(items)
            for offset in range(0, len(section_items), max_sections):
                batch = section_items[offset:offset + max_sections]
                suffix = ""
                if len(section_items) > max_sections:
                    suffix = f"（{offset // max_sections + 1}）"
                chapters.append({
                    "title": f"第{chapter_index}章 {label}{suffix}",
                    "sections": self._build_sections_for_summaries(batch, chapter_index),
                })
                chapter_index += 1

        return chapters or [{"title": f"第{start_chapter}章 {topic}", "sections": []}]

    def _cluster_summaries(self, summaries: list) -> "OrderedDict[str, list]":
        clusters: "OrderedDict[str, list]" = OrderedDict()
        for ms in summaries:
            label = self._cluster_label(ms)
            clusters.setdefault(label, []).append(ms)
        return clusters

    def _cluster_label(self, summary: dict) -> str:
        title = str(summary.get("title") or summary.get("summary") or "")
        tags = [str(tag) for tag in summary.get("tags", []) if tag]
        source_type = str(summary.get("source_type") or "素材")
        haystack = " ".join(tags + [title]).lower()

        rules = [
            ("模型基础与架构", ("transformer", "attention", "mamba", "moe", "architecture", "架构", "注意力")),
            ("大模型训练与微调", ("training", "fine-tuning", "finetune", "peft", "lora", "dpo", "训练", "微调")),
            ("推理优化与部署", ("inference", "serving", "deployment", "flashattention", "speculative", "推理", "部署", "加速")),
            ("智能体与应用开发", ("agent", "rag", "tool", "workflow", "application", "智能体", "应用")),
            ("工程框架与代码实践", ("github", "repository", "repo", "code", "framework", "代码", "工程")),
            ("论文与前沿研究", ("arxiv", "paper", "survey", "论文", "研究")),
            ("课程与教程资料", ("course", "tutorial", "lesson", "教程", "课程")),
        ]
        for label, keywords in rules:
            if any(keyword in haystack for keyword in keywords):
                return label

        source_labels = {
            "arxiv": "论文与前沿研究",
            "github": "工程框架与代码实践",
            "course": "课程与教程资料",
            "course_page": "课程与教程资料",
            "doc_page": "文档与参考资料",
            "web": "网页资料精读",
        }
        return source_labels.get(source_type, "补充资料精读")

    def _expand_long_materials(self, summaries: list) -> list:
        expanded = []
        chunk_chars = self._publisher_cfg().get(
            "fallback_long_material_chunk_chars",
            self.DEFAULT_LONG_MATERIAL_CHARS,
        )
        for ms in summaries:
            content_chars = int(ms.get("content_chars") or 0)
            if content_chars <= chunk_chars:
                expanded.append(ms)
                continue

            parts = max(1, math.ceil(content_chars / chunk_chars))
            for part_index in range(parts):
                start = part_index * chunk_chars
                end = min(content_chars, (part_index + 1) * chunk_chars)
                expanded.append({
                    **ms,
                    "slice_index": part_index + 1,
                    "slice_count": parts,
                    "content_slice": {"start": start, "end": end},
                })
        return expanded

    def _build_sections_for_summaries(self, summaries: list, chapter_index: int) -> List[Dict]:
        sections = []
        grouped = []
        short_group = []
        max_group_size = self._publisher_cfg().get(
            "fallback_section_materials",
            self.DEFAULT_SECTION_MATERIALS,
        )
        group_long_chars = self._publisher_cfg().get(
            "fallback_group_long_material_chars",
            self.DEFAULT_GROUP_LONG_MATERIAL_CHARS,
        )

        for ms in summaries:
            if ms.get("content_slice") or int(ms.get("content_chars") or 0) > group_long_chars:
                if short_group:
                    grouped.append(short_group)
                    short_group = []
                grouped.append([ms])
                continue

            short_group.append(ms)
            if len(short_group) >= max_group_size:
                grouped.append(short_group)
                short_group = []

        if short_group:
            grouped.append(short_group)

        for idx, group in enumerate(grouped, start=1):
            first = group[0]
            base_title = self._section_title(first)
            if len(group) > 1:
                base_title = f"{base_title} 等 {len(group)} 项资料"

            section = {
                "title": f"{chapter_index}.{idx} {base_title}",
                "material_ids": [item["id"] for item in group],
                "description": "；".join(item.get("summary", item["id"])[:120] for item in group),
            }
            material_slices = [
                {
                    "id": item["id"],
                    "start": item["content_slice"]["start"],
                    "end": item["content_slice"]["end"],
                    "part": item.get("slice_index"),
                    "total_parts": item.get("slice_count"),
                }
                for item in group
                if item.get("content_slice")
            ]
            if material_slices:
                section["material_slices"] = material_slices
            sections.append(section)

        return sections

    @staticmethod
    def _section_title(summary: dict) -> str:
        title = str(summary.get("title") or summary.get("summary") or "素材精读")
        title = re.sub(r"\s+", " ", title).strip()
        slice_index = summary.get("slice_index")
        slice_count = summary.get("slice_count")
        if slice_index and slice_count:
            title = f"{title[:36]}（第{slice_index}/{slice_count}部分）"
        return title[:48]

    def _publisher_cfg(self) -> dict:
        return getattr(self, "config", {}).get("publisher", {}) if getattr(self, "config", None) else {}

    def execute(self, input_data: WorkerInput) -> WorkerOutput:
        """Worker接口 - 不直接使用，用plan_book替代"""
        return WorkerOutput(success=True)
