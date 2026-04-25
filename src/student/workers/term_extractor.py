"""
术语提取Worker (TermExtractor)
================================
从内容中提取关键技术术语。
"""

from src.core.worker import BaseWorker, WorkerSpec, WorkerInput, WorkerOutput
from src.utils.logger import logger


class TermExtractor(BaseWorker):
    """术语提取Worker"""

    def __init__(self):
        super().__init__(WorkerSpec(
            name="TermExtractor",
            description="提取关键技术术语",
            model_level="fast",
            max_retries=1,
        ))

    def execute(self, input_data: WorkerInput) -> WorkerOutput:
        content = input_data.content
        if not content:
            return WorkerOutput(success=True, data={"terms": []})

        # 截取前部分用于术语提取（术语提取不需要全文）
        sample = content[:5000] if len(content) > 5000 else content

        try:
            prompt = f"""请从以下技术文本中提取关键术语（名词/专有名词），每行一个。
只提取重要的技术术语、框架名、算法名、概念名等，不超过20个。

文本:
{sample}

请直接输出术语列表，每行一个："""

            result = self.llm_call(
                prompt,
                system="你是技术术语提取专家。只输出术语列表，不要其他内容。",
                temperature=0.3,
            )

            terms = [
                line.strip().strip("-").strip("•").strip()
                for line in result.strip().split("\n")
                if line.strip() and len(line.strip()) < 50
            ]
            # 去重保序
            seen = set()
            unique_terms = []
            for t in terms:
                if t.lower() not in seen:
                    seen.add(t.lower())
                    unique_terms.append(t)

            return WorkerOutput(
                success=True,
                data={"terms": unique_terms[:20]},
            )

        except Exception as e:
            logger.warning(f"术语提取失败: {e}")
            return WorkerOutput(success=True, data={"terms": []})
