"""
代码注释Worker (CodeAnnotator)
================================
为章节中的代码块添加详细的中文注释。
"""

from src.core.worker import BaseWorker, WorkerSpec, WorkerInput, WorkerOutput
from src.utils.logger import logger


class CodeAnnotator(BaseWorker):
    """代码详细注释Worker"""

    def __init__(self):
        super().__init__(WorkerSpec(
            name="CodeAnnotator",
            description="为代码块添加详细中文注释",
            model_level="fast",
            max_retries=1,
        ))

    def execute(self, input_data: WorkerInput) -> WorkerOutput:
        content = input_data.content
        if not content:
            return WorkerOutput(success=True, content="")

        # 查找内容中的代码块并添加注释
        import re
        code_pattern = r'```(\w*)\n(.*?)```'

        def annotate_block(match):
            lang = match.group(1)
            code = match.group(2)

            # 如果代码已经有充足的注释，跳过
            comment_chars = {"python": "#", "javascript": "//", "typescript": "//",
                             "go": "//", "rust": "//", "java": "//", "bash": "#"}
            marker = comment_chars.get(lang, "#")
            comment_lines = sum(1 for line in code.split("\n") if line.strip().startswith(marker))
            total_lines = len([l for l in code.split("\n") if l.strip()])
            if total_lines > 0 and comment_lines / total_lines > 0.3:
                return match.group(0)  # 已有充足注释

            try:
                prompt = f"""请为以下{lang or '代码'}添加详细的中文行注释。
要求：
1. 在关键行添加注释，解释逻辑
2. 不要改变代码本身
3. 注释要简洁准确
4. 只输出添加了注释的代码，不要其他内容

```{lang}
{code}
```"""
                annotated = self.llm_call(prompt, temperature=0.3)

                # 提取代码块
                if f"```{lang}" in annotated:
                    annotated = annotated.split(f"```{lang}")[1].split("```")[0]
                elif "```" in annotated:
                    annotated = annotated.split("```")[1].split("```")[0]

                return f"```{lang}\n{annotated.strip()}\n```"
            except Exception as e:
                logger.warning(f"代码注释失败: {e}")
                return match.group(0)

        annotated_content = re.sub(code_pattern, annotate_block, content, flags=re.DOTALL)

        return WorkerOutput(
            success=True,
            content=annotated_content,
        )
