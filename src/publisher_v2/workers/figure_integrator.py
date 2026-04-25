"""
图片整合排版Worker (FigureIntegrator)
=======================================
将图片描述整合到章节内容中的合适位置。
"""

import re
from src.core.worker import BaseWorker, WorkerSpec, WorkerInput, WorkerOutput
from src.utils.logger import logger


class FigureIntegrator(BaseWorker):
    """图片整合排版Worker"""

    def __init__(self):
        super().__init__(WorkerSpec(
            name="FigureIntegrator",
            description="将图片整合到章节合适位置",
            model_level="fast",
            max_retries=1,
        ))

    def execute(self, input_data: WorkerInput) -> WorkerOutput:
        content = input_data.content
        images = input_data.extra.get("images", [])

        if not content or not images:
            return WorkerOutput(success=True, content=content or "")

        # 将图片占位符替换为Markdown图片引用
        result = content
        for img in images:
            url = img.get("url", "")
            local_path = img.get("local_path", "")
            alt = img.get("alt", "")
            description = img.get("description", "")
            index = img.get("index", 0)

            # 使用本地路径或原始URL
            img_src = local_path if local_path else url
            if not img_src:
                continue

            # 生成Markdown图片标记
            md_image = f"\n\n![{alt or f'图 {index+1}'}]({img_src})"
            if description:
                md_image += f"\n\n> **图 {index+1}**: {description}"

            # 替换占位符
            placeholder = f"[IMAGE_{index}:"
            if placeholder in result:
                # 找到占位符并替换整行
                result = re.sub(
                    rf'\[IMAGE_{index}:.*?\]',
                    md_image.strip(),
                    result,
                )
            else:
                # 没有占位符，追加到内容末尾
                result += md_image

        return WorkerOutput(
            success=True,
            content=result,
        )
