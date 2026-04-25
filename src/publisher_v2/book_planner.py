"""
全书规划器 (BookPlanner)
=========================
从素材库检索素材，规划全书三级目录结构。
"""

import re
import yaml
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
            material_summaries.append({"id": mat.id, "summary": summary})
            priority_view.append(
                {
                    "id": mat.id,
                    "title": mat.title,
                    "quality_score": score or 0,
                    "ready_for_publish": bool(readiness.get("ready_for_publish")),
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
        """降级目录：按素材顺序排列"""
        outline = BookOutline(title=topic)
        chapter = {
            "title": f"第1章 {topic}",
            "sections": []
        }
        for i, ms in enumerate(summaries):
            chapter["sections"].append({
                "title": f"1.{i+1} {ms['summary'][:30]}",
                "material_ids": [ms["id"]],
                "description": ms["summary"],
            })
        outline.chapters.append(chapter)
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

        logger.warning(f"目录规划漏分配 {len(missing_ids)} 条素材，已自动追加补齐章节")
        appendix = {
            "title": "补充素材精读",
            "sections": [],
        }
        summary_by_id = {ms["id"]: ms["summary"] for ms in summaries}
        for idx, material_id in enumerate(missing_ids, start=1):
            summary = summary_by_id.get(material_id, material_id)
            appendix["sections"].append({
                "title": f"补充 {idx}: {summary[:32]}",
                "material_ids": [material_id],
                "description": summary,
            })

        outline.chapters.append(appendix)
        outline.metadata["coverage"] = {
            "total_materials": len(all_ids),
            "assigned_materials": len(all_ids),
            "auto_assigned_materials": len(missing_ids),
        }
        return outline

    def execute(self, input_data: WorkerInput) -> WorkerOutput:
        """Worker接口 - 不直接使用，用plan_book替代"""
        return WorkerOutput(success=True)
