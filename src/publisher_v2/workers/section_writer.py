"""
小节撰写Worker (SectionWriter) — 核心Worker
=============================================
根据素材内容和大纲，撰写深度章节内容。
针对不同类型的素材使用不同的写作prompt。
"""

import math
import re
from typing import List

from src.core.worker import BaseWorker, WorkerSpec, WorkerInput, WorkerOutput
from src.utils.logger import logger


# 不同内容类型的写作提示
_PROMPTS = {
    "tutorial": """你正在为一本技术教程编写章节。
写作要求：
1. 用通俗易懂的语言解释概念
2. 每个新概念都给出示例
3. 代码示例后紧跟逐行解释
4. 循序渐进，从简单到复杂
5. 在关键步骤添加\"注意\"或\"提示\"框""",

    "analysis": """你正在为一本技术分析报告编写章节。
写作要求：
1. 深入分析技术原理和设计决策
2. 对比不同方案的优劣
3. 引用具体的数据和实验结果
4. 分析适用场景和局限性
5. 提供专家级的技术洞察""",

    "paper": """你正在将学术论文改写为易读的技术知识章节。
写作要求：
1. 将学术语言转化为工程师能理解的表述
2. 解释论文的动机和问题定义
3. 用图文并茂的方式解释方法
4. 突出创新点和实际价值
5. 补充实践建议""",

    "code": """你正在为一个开源项目编写技术文档章节。
写作要求：
1. 解释项目的设计思想和架构
2. 关键代码片段配详细注释
3. 说明核心算法的实现逻辑
4. 提供使用示例和最佳实践
5. 讨论扩展和自定义方法""",

    "default": """你正在编写一本AI技术知识库的章节。
写作要求：
1. 内容深度专业但表述清晰
2. 重要概念给出定义和示例
3. 包含代码示例时添加详细注释
4. 图片用文字描述辅助理解
5. 提供延伸阅读建议""",
}


class SectionWriter(BaseWorker):
    """小节深度撰写Worker"""

    def __init__(self):
        super().__init__(WorkerSpec(
            name="SectionWriter",
            description="基于素材深度撰写单个小节",
            model_level="deep",
            max_retries=2,
            timeout=180,
        ))

    def execute(self, input_data: WorkerInput) -> WorkerOutput:
        material_content = input_data.content
        chapter_title = input_data.metadata.get("chapter_title", "")
        section_title = input_data.metadata.get("section_title", "")
        outline = input_data.extra.get("outline", [])
        content_type = input_data.extra.get("content_type", "default")
        images = input_data.extra.get("images", [])
        code_blocks = input_data.extra.get("code_blocks", [])

        if not material_content:
            return WorkerOutput(success=False, error="无素材内容")

        system_prompt = _PROMPTS.get(content_type, _PROMPTS["default"])
        pub_cfg = self.config.get("publisher", {})
        chunk_chars = pub_cfg.get("writer_chunk_chars", 6000)
        overlap_chars = pub_cfg.get("writer_overlap_chars", 500)
        partial_max_tokens = pub_cfg.get("writer_partial_max_tokens", 2200)
        merge_max_tokens = pub_cfg.get("writer_merge_max_tokens", 3200)
        polish_max_tokens = pub_cfg.get("writer_polish_max_tokens", 3200)
        min_section_words = pub_cfg.get("min_section_words", 500)
        max_section_words = pub_cfg.get("max_section_words", 3000)

        outline_text = "\n".join(f"- {p}" for p in outline) if outline else "- 请自行设计结构并保证逻辑完整"
        images_text = self._build_images_text(images)
        code_text = self._build_code_text(code_blocks)
        chunks = self._split_material_content(material_content, chunk_chars, overlap_chars)

        try:
            partial_drafts = []
            for idx, chunk in enumerate(chunks, start=1):
                draft = self._write_chunk(
                    system_prompt=system_prompt,
                    chapter_title=chapter_title,
                    section_title=section_title,
                    outline_text=outline_text,
                    chunk=chunk,
                    chunk_index=idx,
                    chunk_count=len(chunks),
                    images_text=images_text,
                    code_text=code_text,
                    min_section_words=min_section_words,
                    max_section_words=max_section_words,
                    max_tokens=partial_max_tokens,
                )
                partial_drafts.append(draft)

            merged = self._merge_partials(
                partial_drafts=partial_drafts,
                system_prompt=system_prompt,
                chapter_title=chapter_title,
                section_title=section_title,
                outline_text=outline_text,
                max_tokens=merge_max_tokens,
            )

            final_text = self._polish_section(
                merged_text=merged,
                system_prompt=system_prompt,
                chapter_title=chapter_title,
                section_title=section_title,
                outline_text=outline_text,
                images_text=images_text,
                code_text=code_text,
                min_section_words=min_section_words,
                max_section_words=max_section_words,
                max_tokens=polish_max_tokens,
            )

            metrics = self._collect_metrics(
                source_text=material_content,
                final_text=final_text,
                partial_drafts=partial_drafts,
                min_section_words=min_section_words,
            )

            return WorkerOutput(
                success=True,
                content=final_text,
                data=metrics,
            )

        except Exception as e:
            logger.error(f"章节撰写失败: {e}")
            return WorkerOutput(success=False, error=str(e))

    def _write_chunk(
        self,
        system_prompt: str,
        chapter_title: str,
        section_title: str,
        outline_text: str,
        chunk: str,
        chunk_index: int,
        chunk_count: int,
        images_text: str,
        code_text: str,
        min_section_words: int,
        max_section_words: int,
        max_tokens: int,
    ) -> str:
        target_words = max(300, math.ceil(max_section_words / max(1, chunk_count)))
        prompt = f"""请基于当前素材片段，为技术书籍章节撰写一份可合并的高质量分稿。

## 章节信息
章: {chapter_title}
节: {section_title}
当前片段: {chunk_index}/{chunk_count}

## 参考大纲
{outline_text}

## 当前素材片段
{chunk}

## 可参考的图片描述
{images_text or '（无）'}

## 可参考的代码片段
{code_text or '（无）'}

## 输出要求
1. 只输出 Markdown 正文，标题层级从 `##` 开始
2. 只覆盖当前素材片段中能支撑的要点，不要凭空补全未出现的信息
3. 解释必须充分，避免摘抄原文
4. 如使用代码，必须加简短注释或解释
5. 目标篇幅约 {target_words} 字，宁可信息密实，也不要空话
6. 如果引用论文、仓库、课程或外部资料，请在相关段落中自然注明来源标题或来源类型
7. 结尾不要写“本片段结束”“待续”之类的话"""
        return self.llm_call(
            prompt,
            system=system_prompt,
            enable_thinking=True,
            max_tokens=max_tokens,
        ).strip()

    def _merge_partials(
        self,
        partial_drafts: List[str],
        system_prompt: str,
        chapter_title: str,
        section_title: str,
        outline_text: str,
        max_tokens: int,
    ) -> str:
        drafts = [draft.strip() for draft in partial_drafts if draft and draft.strip()]
        if not drafts:
            raise ValueError("所有分稿均为空")
        if len(drafts) == 1:
            return drafts[0]

        merge_batch_size = 3
        current = drafts
        while len(current) > 1:
            next_round = []
            for idx in range(0, len(current), merge_batch_size):
                batch = current[idx:idx + merge_batch_size]
                if len(batch) == 1:
                    next_round.append(batch[0])
                    continue
                merged = self._merge_batch(
                    batch=batch,
                    system_prompt=system_prompt,
                    chapter_title=chapter_title,
                    section_title=section_title,
                    outline_text=outline_text,
                    max_tokens=max_tokens,
                )
                next_round.append(merged)
            current = next_round
        return current[0]

    def _merge_batch(
        self,
        batch: List[str],
        system_prompt: str,
        chapter_title: str,
        section_title: str,
        outline_text: str,
        max_tokens: int,
    ) -> str:
        partials_text = "\n\n".join(
            f"### 分稿 {idx + 1}\n{draft}" for idx, draft in enumerate(batch)
        )
        prompt = f"""请将以下同一章节的多份分稿合并为一份连贯、去重、结构统一的章节正文。

## 章节信息
章: {chapter_title}
节: {section_title}

## 参考大纲
{outline_text}

## 待合并分稿
{partials_text}

## 输出要求
1. 只输出 Markdown 正文，标题层级从 `##` 开始
2. 合并重复内容，保留最有信息量的解释
3. 调整段落顺序，让逻辑更顺
4. 不要丢失关键事实、代码说明和案例
5. 不要出现“分稿1”“分稿2”等痕迹"""
        return self.llm_call(
            prompt,
            system=system_prompt,
            enable_thinking=True,
            max_tokens=max_tokens,
        ).strip()

    def _polish_section(
        self,
        merged_text: str,
        system_prompt: str,
        chapter_title: str,
        section_title: str,
        outline_text: str,
        images_text: str,
        code_text: str,
        min_section_words: int,
        max_section_words: int,
        max_tokens: int,
    ) -> str:
        prompt = f"""请将下面的章节草稿润色为最终版技术书籍内容。

## 章节信息
章: {chapter_title}
节: {section_title}

## 参考大纲
{outline_text}

## 图片描述
{images_text or '（无）'}

## 代码片段
{code_text or '（无）'}

## 当前草稿
{merged_text}

## 最终输出要求
1. 只输出 Markdown 正文，标题层级从 `##` 开始
2. 信息完整、表达专业、结构清晰
3. 如果存在代码或图片信息，在合适位置自然融入解释
4. 如果使用外部事实、论文结论、仓库实现或课程材料，请在正文中保留来源线索（标题、类型或材料名）
5. 结尾必须有一个简短小结
6. 控制在 {min_section_words}-{max_section_words} 字范围内
7. 不要输出与章节无关的前言或免责声明"""
        return self.llm_call(
            prompt,
            system=system_prompt,
            enable_thinking=True,
            max_tokens=max_tokens,
        ).strip()

    @staticmethod
    def _split_material_content(content: str, chunk_chars: int, overlap_chars: int) -> List[str]:
        if len(content) <= chunk_chars:
            return [content]

        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", content) if p.strip()]
        chunks = []
        current = []
        current_len = 0

        for para in paragraphs:
            para_len = len(para) + 2
            if current and current_len + para_len > chunk_chars:
                chunks.append("\n\n".join(current))
                overlap = []
                overlap_len = 0
                for prev in reversed(current):
                    overlap.insert(0, prev)
                    overlap_len += len(prev) + 2
                    if overlap_len >= overlap_chars:
                        break
                current = overlap[:]
                current_len = sum(len(item) + 2 for item in current)
            current.append(para)
            current_len += para_len

        if current:
            chunks.append("\n\n".join(current))

        return chunks or [content]

    @staticmethod
    def _build_images_text(images: list) -> str:
        lines = []
        for img in images[:10]:
            desc = img.get("description", img.get("alt", ""))
            if desc:
                lines.append(f"- 图片: {desc}")
        return "\n".join(lines)

    @staticmethod
    def _build_code_text(code_blocks: list) -> str:
        blocks = []
        for cb in code_blocks[:5]:
            lang = cb.get("language", "")
            code = cb.get("code", "")[:500]
            comment = cb.get("comment", "")
            blocks.append(f"```{lang}\n{code}\n```\n{comment}".strip())
        return "\n\n".join(blocks)

    @staticmethod
    def _estimate_length_units(text: str) -> int:
        chinese_chars = re.findall(r"[\u4e00-\u9fff]", text)
        latin_words = re.findall(r"[A-Za-z0-9_]+", text)
        return len(chinese_chars) + len(latin_words)

    def _collect_metrics(
        self,
        source_text: str,
        final_text: str,
        partial_drafts: List[str],
        min_section_words: int,
    ) -> dict:
        estimated_units = self._estimate_length_units(final_text)
        abrupt_end = not final_text.rstrip().endswith(("。", "！", "？", ".", "`", "|"))
        too_short = estimated_units < max(200, int(min_section_words * 0.65))
        heading_count = final_text.count("## ")
        return {
            "word_count": len(final_text),
            "estimated_length_units": estimated_units,
            "content_type": "chunked",
            "chunk_count": len(partial_drafts),
            "source_chars": len(source_text),
            "heading_count": heading_count,
            "too_short": too_short,
            "abrupt_end": abrupt_end,
            "quality_flags": [
                flag for flag, enabled in {
                    "too_short": too_short,
                    "abrupt_end": abrupt_end,
                    "missing_headings": heading_count == 0,
                }.items() if enabled
            ],
        }
