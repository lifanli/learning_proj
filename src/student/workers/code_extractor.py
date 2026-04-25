"""
代码提取Worker (CodeExtractor)
===============================
从页面内容中提取代码块，添加语言检测和注释。
"""

import re
from src.core.worker import BaseWorker, WorkerSpec, WorkerInput, WorkerOutput
from src.utils.logger import logger


class CodeExtractor(BaseWorker):
    """代码块提取+注释Worker"""

    def __init__(self):
        super().__init__(WorkerSpec(
            name="CodeExtractor",
            description="提取代码块并添加简要注释",
            model_level="fast",
            max_retries=1,
        ))

    def execute(self, input_data: WorkerInput) -> WorkerOutput:
        content = input_data.content
        if not content:
            return WorkerOutput(success=True, data={"code_blocks": []})

        # 提取Markdown代码块
        code_blocks = self._extract_code_blocks(content)

        # 用LLM添加简要注释（如果代码块不为空）
        if code_blocks:
            code_blocks = self._annotate_blocks(code_blocks)

        return WorkerOutput(
            success=True,
            data={"code_blocks": code_blocks},
        )

    def _extract_code_blocks(self, text: str) -> list:
        """从文本中提取代码块"""
        blocks = []
        # Markdown 代码块
        pattern = r'```(\w*)\n(.*?)```'
        for match in re.finditer(pattern, text, re.DOTALL):
            lang = match.group(1) or self._detect_language(match.group(2))
            code = match.group(2).strip()
            if len(code) > 10:  # 过滤太短的片段
                blocks.append({
                    "language": lang,
                    "code": code,
                    "comment": "",
                })
        return blocks

    def _detect_language(self, code: str) -> str:
        """简单的语言检测"""
        indicators = {
            "python": [r'\bdef\s+\w+', r'\bimport\s+\w+', r'\bclass\s+\w+.*:', r'print\('],
            "javascript": [r'\bconst\s+\w+', r'\bfunction\s+\w+', r'=>', r'\bconsole\.log'],
            "typescript": [r'\binterface\s+\w+', r':\s*\w+\[\]', r'\btype\s+\w+\s*='],
            "rust": [r'\bfn\s+\w+', r'\blet\s+mut\b', r'\bimpl\s+', r'::'],
            "go": [r'\bfunc\s+\w+', r'\bpackage\s+\w+', r':='],
            "bash": [r'^#!/bin/', r'\becho\s+', r'\bexport\s+'],
        }
        for lang, patterns in indicators.items():
            matches = sum(1 for p in patterns if re.search(p, code, re.MULTILINE))
            if matches >= 2:
                return lang
        return ""

    def _annotate_blocks(self, blocks: list) -> list:
        """用LLM为代码块添加简要注释"""
        # 批量处理以减少API调用
        batch_text = ""
        for i, block in enumerate(blocks):
            batch_text += f"\n---CODE_BLOCK_{i}---\nLanguage: {block['language']}\n{block['code'][:500]}\n"

        if not batch_text:
            return blocks

        try:
            prompt = f"""请为以下每个代码块写一句简要的中文注释（说明这段代码做了什么）。
格式：每行一个，BLOCK_N: 注释

{batch_text}"""

            result = self.llm_call(prompt, system="你是代码注释专家。为每段代码写简洁的中文注释。")

            # 解析结果
            for i, block in enumerate(blocks):
                marker = f"BLOCK_{i}:"
                for line in result.split("\n"):
                    if marker in line:
                        block["comment"] = line.split(marker, 1)[1].strip()
                        break

        except Exception as e:
            logger.warning(f"代码注释生成失败: {e}")

        return blocks
