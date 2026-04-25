"""
知识缺口检测Worker (GapDetector)
==================================
分析已收集素材，发现知识缺口，建议补充学习。
"""

from src.core.worker import BaseWorker, WorkerSpec, WorkerInput, WorkerOutput
from src.utils.logger import logger


class GapDetector(BaseWorker):
    """知识缺口检测Worker"""

    def __init__(self):
        super().__init__(WorkerSpec(
            name="GapDetector",
            description="检测知识缺口，建议补充学习方向",
            model_level="deep",
            max_retries=1,
        ))

    def execute(self, input_data: WorkerInput) -> WorkerOutput:
        content = input_data.content
        existing_topics = input_data.extra.get("existing_topics", [])
        existing_terms = input_data.extra.get("existing_terms", [])

        if not content:
            return WorkerOutput(success=True, data={"gaps": [], "suggestions": []})

        try:
            prompt = f"""分析以下已收集的学习素材，检测知识缺口。

已收集的素材主题：
{chr(10).join(f'- {t}' for t in existing_topics[:20])}

已收集的术语列表：
{', '.join(existing_terms[:30])}

当前内容概要：
{content[:3000]}

请分析：
1. 内容中提到但未深入覆盖的概念（知识缺口）
2. 相关但未涉及的重要主题
3. 建议补充学习的搜索关键词

格式：
## 知识缺口
- ...

## 建议补充
- 主题: 搜索关键词"""

            result = self.llm_call(
                prompt,
                system="你是AI领域教育专家。帮助发现学习盲点。",
                enable_thinking=True,
            )

            # 解析缺口和建议
            gaps = []
            suggestions = []
            current_section = None

            for line in result.split("\n"):
                line = line.strip()
                if "知识缺口" in line:
                    current_section = "gaps"
                elif "建议补充" in line:
                    current_section = "suggestions"
                elif line.startswith("-") and current_section:
                    item = line.lstrip("-").strip()
                    if current_section == "gaps":
                        gaps.append(item)
                    else:
                        suggestions.append(item)

            return WorkerOutput(
                success=True,
                content=result,
                data={"gaps": gaps, "suggestions": suggestions},
            )

        except Exception as e:
            logger.warning(f"知识缺口检测失败: {e}")
            return WorkerOutput(success=True, data={"gaps": [], "suggestions": []})
