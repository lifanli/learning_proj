"""
图片Worker (ImageWorker)
========================
下载图片 + 使用VL模型解读图片内容。
"""

import os
import base64
from src.core.worker import BaseWorker, WorkerSpec, WorkerInput, WorkerOutput
from src.tools.web_browser import WebBrowser
from src.utils.logger import logger


class ImageWorker(BaseWorker):
    """图片下载+VL解读Worker"""

    def __init__(self):
        super().__init__(WorkerSpec(
            name="ImageWorker",
            description="下载图片并使用VL模型解读",
            model_level="deep",
            max_retries=1,
            timeout=120,
        ))
        self.browser = WebBrowser()

    def execute(self, input_data: WorkerInput) -> WorkerOutput:
        images = input_data.extra.get("images", [])
        save_dir = input_data.extra.get("save_dir", "data/materials/temp/images")
        interpret = input_data.extra.get("interpret", True)

        if not images:
            return WorkerOutput(success=True, data={"images": []})

        results = []
        for img_info in images:
            url = img_info.get("url", "")
            if not url:
                continue

            # 过滤广告/装饰图片
            if self._is_ad_image(url, img_info):
                continue

            # 跳过 VL 模型不支持的格式
            if url.lower().endswith(".svg") or ".svg?" in url.lower():
                logger.debug(f"跳过 SVG 图片: {url}")
                continue

            result = {"url": url, "alt": img_info.get("alt", ""), "local_path": "", "description": ""}

            # 下载图片
            local_path = self.browser.download_image(url, save_dir)
            if local_path:
                result["local_path"] = local_path

                # VL解读
                if interpret:
                    try:
                        description = self._interpret_image(url, img_info.get("alt", ""), local_path)
                        result["description"] = description
                    except Exception as e:
                        logger.warning(f"图片解读失败 {url}: {e}")

            results.append(result)

        return WorkerOutput(
            success=True,
            data={"images": results},
        )

    def _interpret_image(self, image_url: str, alt_text: str = "", local_path: str = "") -> str:
        """使用VL模型解读图片"""
        prompt = "请详细描述这张图片的内容。"
        if alt_text:
            prompt += f"\n图片的alt文本是: {alt_text}"
        prompt += "\n如果是技术架构图、流程图或代码截图，请详细描述其中的关键信息。"

        # 优先用本地文件转base64，避免API远程下载超时
        actual_url = image_url
        if local_path and os.path.exists(local_path):
            actual_url = self._to_base64_url(local_path)

        return self.llm_call_with_images(
            prompt=prompt,
            image_urls=[actual_url],
            system="你是一个技术图片分析专家。请用中文描述图片内容，重点关注技术细节。",
        )

    MAX_IMAGE_BYTES = 5 * 1024 * 1024  # Anthropic API 限制 5MB

    @staticmethod
    def _detect_mime_from_bytes(header: bytes) -> str:
        """通过文件头魔术字节检测真实 MIME 类型"""
        if header[:3] == b'\xff\xd8\xff':
            return "image/jpeg"
        if header[:8] == b'\x89PNG\r\n\x1a\n':
            return "image/png"
        if header[:4] == b'RIFF' and header[8:12] == b'WEBP':
            return "image/webp"
        if header[:6] in (b'GIF87a', b'GIF89a'):
            return "image/gif"
        if header[:4] == b'\x00\x00\x00\x1c' or header[:4] == b'\x00\x00\x00\x20':
            return "image/avif"
        return "image/png"  # fallback

    @classmethod
    def _to_base64_url(cls, file_path: str) -> str:
        """将本地图片文件转为 base64 data URI，基于文件内容检测真实 MIME 类型"""
        file_size = os.path.getsize(file_path)
        if file_size > cls.MAX_IMAGE_BYTES:
            raise ValueError(
                f"图片过大 ({file_size / 1024 / 1024:.1f}MB > 5MB): {file_path}"
            )
        with open(file_path, "rb") as f:
            raw = f.read()
        mime_type = cls._detect_mime_from_bytes(raw[:12])
        data = base64.b64encode(raw).decode("utf-8")
        return f"data:{mime_type};base64,{data}"

    def _is_ad_image(self, url: str, img_info: dict) -> bool:
        """判断是否为广告/装饰图片"""
        url_lower = url.lower()

        # URL关键词过滤
        ad_keywords = ["qrcode", "reward", "donate", "sponsor", "ad_", "banner", "tracking"]
        if any(kw in url_lower for kw in ad_keywords):
            return True

        # 小图标过滤
        alt = img_info.get("alt", "").lower()
        if any(kw in alt for kw in ["icon", "logo", "badge", "shield"]):
            return True

        # GIF装饰过滤
        if url_lower.endswith(".gif") and "mmbiz" in url_lower:
            return True

        return False
