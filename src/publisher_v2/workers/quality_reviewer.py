"""
质量审核Worker (QualityReviewer)
==================================
审核章节质量：完整性、准确性、可读性。
"""

from src.core.worker import BaseWorker, WorkerSpec, WorkerInput, WorkerOutput
from src.utils.logger import logger


class QualityReviewer(BaseWorker):
    """质量审核Worker"""

    def __init__(self):
        super().__init__(WorkerSpec(
            name="QualityReviewer",
            description="审核章节质量并提出修改建议",
            model_level="deep",
            max_retries=1,
            timeout=120,
        ))

    def execute(self, input_data: WorkerInput) -> WorkerOutput:
        content = input_data.content
        section_title = input_data.metadata.get("section_title", "")

        if not content:
            return WorkerOutput(success=False, error="章节内容为空", data={"passed": False, "issues": ["章节内容为空"]})

        prompt = f"""请审核以下技术章节的质量。

标题: {section_title}

内容样本:
{self._sample_content(content)}

请检查以下方面并评分（1-5分）：
1. 完整性：是否覆盖了标题承诺的所有内容
2. 准确性：技术描述是否正确
3. 深度：是否有足够的技术深度
4. 可读性：表述是否清晰易懂
5. 结构：组织是否合理

如果发现问题，请指出具体位置和修改建议。

格式：
SCORE: X/5
PASSED: yes/no
ISSUES:
- 问题1
- 问题2
SUGGESTIONS:
- 建议1"""

        try:
            result = self.llm_call(
                prompt,
                system="你是技术文档质量审核专家。严格但公正地评估内容质量。",
                enable_thinking=True,
                max_tokens=1800,
            )

            result_lower = result.lower()
            passed = "passed: yes" in result_lower or "passed:yes" in result_lower
            issues = []
            suggestions = []
            current_section = None

            for raw_line in result.split("\n"):
                line = raw_line.strip()
                upper = line.upper()
                if upper.startswith("ISSUES"):
                    current_section = "issues"
                elif upper.startswith("SUGGESTIONS"):
                    current_section = "suggestions"
                elif line.startswith("- ") and current_section:
                    item = line[2:].strip()
                    if current_section == "issues":
                        issues.append(item)
                    else:
                        suggestions.append(item)

            return WorkerOutput(
                success=True,
                content=result,
                data={
                    "passed": passed,
                    "issues": issues,
                    "suggestions": suggestions,
                    "sampled": True,
                },
            )

        except Exception as e:
            logger.warning(f"质量审核失败: {e}")
            return WorkerOutput(
                success=False,
                error=str(e),
                data={
                    "passed": False,
                    "issues": [f"质量审核失败: {e}"],
                    "suggestions": ["请检查模型输出限制或审核超时设置"],
                },
            )

    @staticmethod
    def _sample_content(content: str, window: int = 2200) -> str:
        if len(content) <= window * 3:
            return content

        middle_start = max(0, len(content) // 2 - window // 2)
        middle_end = middle_start + window
        parts = [
            "[开头]\n" + content[:window],
            "[中间]\n" + content[middle_start:middle_end],
            "[结尾]\n" + content[-window:],
        ]
        return "\n\n...\n\n".join(parts)
