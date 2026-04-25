"""
主题标签Worker (TopicTagger)
==============================
为素材自动标注主题标签。
"""

from src.core.worker import BaseWorker, WorkerSpec, WorkerInput, WorkerOutput
from src.utils.logger import logger


class TopicTagger(BaseWorker):
    """主题标签标注Worker"""

    def __init__(self):
        super().__init__(WorkerSpec(
            name="TopicTagger",
            description="为素材自动标注主题标签",
            model_level="fast",
            max_retries=1,
        ))

    def execute(self, input_data: WorkerInput) -> WorkerOutput:
        content = input_data.content
        title = input_data.metadata.get("title", "")
        if not content and not title:
            return WorkerOutput(success=True, data={"tags": []})

        sample = content[:3000] if len(content) > 3000 else content

        try:
            prompt = f"""请为以下技术内容标注3-5个主题标签。

标题: {title}
内容摘要:
{sample}

要求：
1. 使用中文标签
2. 包含技术领域标签（如：大语言模型、强化学习、计算机视觉）
3. 包含技术栈标签（如：PyTorch、Transformer、LangChain）
4. 包含应用场景标签（如：对话系统、代码生成、文档问答）

请直接输出标签，每行一个："""

            result = self.llm_call(
                prompt,
                system="你是技术内容分类专家。只输出标签列表。",
                temperature=0.3,
            )

            tags = [
                line.strip().strip("-").strip("•").strip("#").strip()
                for line in result.strip().split("\n")
                if line.strip() and len(line.strip()) < 30
            ]

            return WorkerOutput(
                success=True,
                data={"tags": tags[:5]},
            )

        except Exception as e:
            logger.warning(f"标签标注失败: {e}")
            return WorkerOutput(success=True, data={"tags": []})
