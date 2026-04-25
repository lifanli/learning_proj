"""
交叉引用Worker (CrossReferencer)
==================================
在章节之间添加交叉引用链接。
"""

from src.core.worker import BaseWorker, WorkerSpec, WorkerInput, WorkerOutput
from src.utils.logger import logger


class CrossReferencer(BaseWorker):
    """交叉引用Worker"""

    def __init__(self):
        super().__init__(WorkerSpec(
            name="CrossReferencer",
            description="添加章节间交叉引用",
            model_level="fast",
            max_retries=1,
        ))

    def execute(self, input_data: WorkerInput) -> WorkerOutput:
        content = input_data.content
        all_sections = input_data.extra.get("all_sections", [])
        # all_sections: [{"title": str, "file_path": str}]
        current_title = input_data.metadata.get("section_title", "")

        if not content:
            return WorkerOutput(success=True, content="")

        # 在正文前部插入轻量来源提示
        source_materials = input_data.extra.get("source_materials", [])
        inline_hint = self._build_inline_source_hint(source_materials)
        if inline_hint:
            content = self._inject_inline_hint(content, inline_hint)

        # 在内容末尾添加相关章节引用
        related = self._find_related_sections(content, all_sections, current_title)

        if related:
            content += "\n\n---\n\n**相关章节：**\n"
            for section in related[:5]:
                content += f"- [{section['title']}]({section['file_path']})\n"

        # 添加源材料链接
        source_urls = input_data.extra.get("source_urls", [])
        sources_block = self._build_sources_block(source_materials, source_urls)
        if sources_block:
            content += f"\n\n---\n\n{sources_block}"

        return WorkerOutput(
            success=True,
            content=content,
        )

    def _find_related_sections(self, content: str, all_sections: list, current_title: str) -> list:
        """基于关键词匹配找到相关章节"""
        # 简单实现：从当前内容提取关键词，匹配其他章节标题
        content_lower = content.lower()
        related = []

        for section in all_sections:
            title = section.get("title", "")
            if title == current_title:
                continue

            # 计算标题中的词在内容中出现的次数
            words = [w for w in title.lower().split() if len(w) > 2]
            if not words:
                continue

            matches = sum(1 for w in words if w in content_lower)
            if matches >= len(words) * 0.3:
                related.append(section)

        return related

    @staticmethod
    def _build_sources_block(source_materials: list, source_urls: list) -> str:
        lines = []
        seen_urls = set()

        if source_materials:
            lines.append("**来源与延伸阅读：**")
            for material in source_materials[:10]:
                title = material.get("title") or material.get("source_url") or material.get("id") or "未命名素材"
                source_type = material.get("source_type") or "source"
                source_url = material.get("source_url") or ""
                base_line = f"- [{source_type}] {title}"
                if source_url:
                    base_line += f" - {source_url}"
                    seen_urls.add(source_url)
                lines.append(base_line)

                for ref in (material.get("references") or [])[:5]:
                    ref_title = ref.get("title") or ref.get("url") or "未命名引用"
                    ref_type = ref.get("type") or "reference"
                    ref_url = ref.get("url") or ""
                    if ref_url:
                        seen_urls.add(ref_url)
                        lines.append(f"  - 延伸 [{ref_type}] {ref_title} - {ref_url}")
                    else:
                        lines.append(f"  - 延伸 [{ref_type}] {ref_title}")

        extra_urls = []
        for url in source_urls[:10]:
            if url and url not in seen_urls:
                extra_urls.append(url)
                seen_urls.add(url)

        if extra_urls:
            if not lines:
                lines.append("**来源与延伸阅读：**")
            for url in extra_urls:
                lines.append(f"- [source] {url}")

        return "\n".join(lines)

    @staticmethod
    def _build_inline_source_hint(source_materials: list) -> str:
        labels = []
        for material in source_materials[:3]:
            title = material.get("title") or material.get("source_url") or material.get("id")
            if not title:
                continue
            source_type = material.get("source_type") or "source"
            labels.append(f"[{source_type}] {title}")

        if not labels:
            return ""
        return "_来源提示：" + "；".join(labels) + "_"

    @staticmethod
    def _inject_inline_hint(content: str, inline_hint: str) -> str:
        if not inline_hint or inline_hint in content:
            return content

        parts = content.split("\n\n", 1)
        if len(parts) == 2 and parts[0].lstrip().startswith("#"):
            return f"{parts[0]}\n\n{inline_hint}\n\n{parts[1]}"
        return f"{inline_hint}\n\n{content}"
