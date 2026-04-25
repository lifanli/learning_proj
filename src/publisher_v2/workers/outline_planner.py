"""
章节大纲规划Worker (OutlinePlanner)
=====================================
为单个章节规划详细的小节大纲。
"""

from src.core.worker import BaseWorker, WorkerSpec, WorkerInput, WorkerOutput
from src.utils.logger import logger


class OutlinePlanner(BaseWorker):
    """章节大纲规划Worker"""

    def __init__(self):
        super().__init__(WorkerSpec(
            name="OutlinePlanner",
            description="规划单章的详细小节大纲",
            model_level="fast",
            max_retries=1,
        ))

    def execute(self, input_data: WorkerInput) -> WorkerOutput:
        chapter_title = input_data.metadata.get("chapter_title", "")
        section_title = input_data.metadata.get("section_title", "")
        section_description = input_data.metadata.get("description", "")
        material_content = input_data.content
        max_context = self.config.get("publisher", {}).get("max_context_chars", 5000)

        if not material_content:
            return WorkerOutput(success=True, data={"outline": []})

        prompt = f"""请为以下章节规划详细的写作大纲。

章标题: {chapter_title}
节标题: {section_title}
节描述: {section_description}

可用素材内容概要（完整内容将在写作时提供）:
{material_content[:max_context]}

请设计本节的详细大纲，包括：
1. 引言（为什么重要）
2. 核心概念解释
3. 技术细节/实现方法
4. 代码示例说明（如有）
5. 小结

每个点用一行，格式：
- 大纲点标题: 简要说明"""

        try:
            result = self.llm_call(
                prompt,
                system="你是技术书籍大纲规划专家。设计清晰、有深度的章节大纲。",
                temperature=0.5,
            )

            outline_points = []
            for line in result.strip().split("\n"):
                line = line.strip()
                if line.startswith("-") or line.startswith("*"):
                    outline_points.append(line.lstrip("-*").strip())

            return WorkerOutput(
                success=True,
                content=result,
                data={"outline": outline_points},
            )

        except Exception as e:
            logger.warning(f"大纲规划失败: {e}")
            return WorkerOutput(success=True, data={"outline": [section_title]})
