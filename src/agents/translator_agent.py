import re
from src.agents.base_agent import BaseAgent
from src.utils.logger import logger


class TranslatorAgent(BaseAgent):
    """翻译智能体：检测非中文内容并翻译为中文，保留术语/代码/URL"""

    def __init__(self):
        super().__init__(
            role_name="翻译员",
            role_instruction=(
                "你是一名专业的技术文档翻译员。你的任务是将英文技术内容翻译为流畅、专业的中文。\n"
                "翻译规则：\n"
                "1. 保留所有代码片段、URL 链接、文件路径不翻译\n"
                "2. 保留专有名词的英文原文，格式为：中文翻译(English Original)\n"
                "3. 保留 Markdown 格式标记\n"
                "4. 技术术语首次出现时附注英文，后续可直接使用中文\n"
                "5. 如果内容已经是中文，直接原样输出"
            )
        )
        self.chinese_threshold = 0.30  # 中文字符占比阈值

    def _is_chinese_dominant(self, text: str) -> bool:
        """检测文本是否以中文为主（中文字符占比 >= 阈值）"""
        if not text.strip():
            return True

        # 匹配中文字符（CJK 统一表意文字）
        chinese_chars = re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', text)
        # 匹配所有字母数字字符（排除空格、标点等）
        all_alpha_chars = re.findall(r'[\u4e00-\u9fff\u3400-\u4dbfa-zA-Z]', text)

        if not all_alpha_chars:
            return True

        ratio = len(chinese_chars) / len(all_alpha_chars)
        return ratio >= self.chinese_threshold

    def translate(self, text: str) -> str:
        """
        检测内容语言，若非中文主导则翻译为中文。
        返回中文内容。
        """
        if not text or not text.strip():
            return text

        if self._is_chinese_dominant(text):
            logger.info("内容已为中文，跳过翻译")
            return text

        logger.info("检测到非中文内容，开始翻译...")

        prompt = (
            "请将以下技术内容翻译为专业的中文。保留代码、URL、文件路径不翻译。"
            "专有名词首次出现时附注英文原文。直接输出翻译结果，不要添加额外说明。\n\n"
            f"---\n{text}\n---"
        )

        result = self.chat(prompt, stream=False)
        if result and not result.startswith("Error:"):
            logger.info("翻译完成")
            return result
        else:
            logger.warning(f"翻译失败，返回原文: {result}")
            return text
