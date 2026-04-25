"""
页面抓取Worker (ContentFetcher)
================================
抓取页面完整内容+图片位置，不截断。
"""

from src.core.worker import BaseWorker, WorkerSpec, WorkerInput, WorkerOutput
from src.core.material_store import Material
from src.tools.web_browser import WebBrowser
from src.utils.logger import logger


class ContentFetcher(BaseWorker):
    """页面内容抓取Worker"""

    def __init__(self):
        super().__init__(WorkerSpec(
            name="ContentFetcher",
            description="抓取网页完整内容（不截断），保留图片和代码块位置",
            model_level="fast",
            max_retries=2,
            timeout=30,
        ))
        self.browser = WebBrowser()

    def execute(self, input_data: WorkerInput) -> WorkerOutput:
        url = input_data.url
        if not url:
            return WorkerOutput(success=False, error="缺少URL")

        html = self.browser.fetch_page(url)
        if not html:
            return WorkerOutput(success=False, error=f"无法获取页面: {url}")

        # 提取带图片的完整内容
        extracted = self.browser.extract_content_with_images(html, url)
        title = self.browser.extract_title(html) or ""

        # 构建Material
        material = Material(
            source_url=url,
            source_type=input_data.metadata.get("source_type", "web"),
            title=title,
            content=extracted["text"],
            parent_id=input_data.parent_id,
            order_index=input_data.metadata.get("order", 0),
            images=[
                {"url": img["url"], "alt": img.get("alt", ""), "local_path": ""}
                for img in extracted["images"]
            ],
            code_blocks=[
                {"language": cb["language"], "code": cb["code"], "comment": ""}
                for cb in extracted["code_blocks"]
            ],
            metadata={
                "headings": extracted["headings"],
                "raw_html_length": len(html),
            }
        )

        return WorkerOutput(
            success=True,
            content=extracted["text"],
            data={
                "title": title,
                "images": extracted["images"],
                "code_blocks": extracted["code_blocks"],
                "headings": extracted["headings"],
            },
            materials=[material],
        )
