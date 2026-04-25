"""
分段翻译Worker (TranslatorWorker)
====================================
对长文本进行分段翻译，不截断。
"""

import re
from src.core.worker import BaseWorker, WorkerSpec, WorkerInput, WorkerOutput
from src.utils.logger import logger


class TranslatorWorker(BaseWorker):
    """分段翻译Worker"""

    def __init__(self):
        super().__init__(WorkerSpec(
            name="TranslatorWorker",
            description="分段翻译长文本，保留代码块和技术术语",
            model_level="fast",
            max_retries=2,
            timeout=300,
        ))

    def execute(self, input_data: WorkerInput) -> WorkerOutput:
        content = input_data.content
        if not content:
            return WorkerOutput(success=True, content="")

        # 检测是否需要翻译
        if self._is_chinese_dominant(content):
            return WorkerOutput(success=True, content=content, data={"language": "zh", "translated": False})

        # 分段翻译
        segments = self._split_content(content)
        translated_segments = []

        for i, segment in enumerate(segments):
            if self._is_code_block(segment):
                # 代码块不翻译
                translated_segments.append(segment)
            elif len(segment.strip()) < 10:
                translated_segments.append(segment)
            else:
                try:
                    translated = self._translate_segment(segment)
                    translated_segments.append(translated)
                except Exception as e:
                    logger.warning(f"翻译第{i}段失败: {e}")
                    translated_segments.append(segment)

        result = "\n\n".join(translated_segments)
        return WorkerOutput(
            success=True,
            content=result,
            data={"language": "en", "translated": True, "segments": len(segments)},
        )

    def _is_chinese_dominant(self, text: str) -> bool:
        """检测文本是否以中文为主"""
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        total_alpha = len(re.findall(r'[\w]', text))
        if total_alpha == 0:
            return True
        return chinese_chars / total_alpha > 0.3

    def _split_content(self, text: str, max_segment: int = 1200) -> list:
        """按段落分割文本，每段不超过max_segment字符"""
        paragraphs = text.split("\n\n")
        segments = []
        current = ""

        for para in paragraphs:
            if len(current) + len(para) > max_segment and current:
                segments.append(current.strip())
                current = para
            else:
                current += "\n\n" + para if current else para

        if current.strip():
            segments.append(current.strip())

        return segments

    def _is_code_block(self, text: str) -> bool:
        """检测是否为代码块"""
        return text.strip().startswith("```") and text.strip().endswith("```")

    def _translate_segment(self, text: str) -> str:
        """翻译单个段落"""
        prompt = f"""请将以下英文技术文本翻译为专业的中文。
要求：
1. 保留所有代码、URL、技术术语的原文
2. 首次出现的专业术语在中文后括号内注明英文
3. 保持原文格式（标题、列表、引用等）
4. 翻译要自然流畅，不要逐字翻译

原文：
{text}"""

        return self.llm_call(
            prompt,
            system="你是专业的AI技术文档翻译专家。",
            temperature=0.3,
        )
