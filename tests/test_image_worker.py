"""
test_image_worker.py — ImageWorker (base64/广告过滤) 测试
"""

import os
import base64
from unittest.mock import patch, MagicMock
import pytest

from src.student.workers.image_worker import ImageWorker


# ---------------------------------------------------------------------------
# 纯逻辑测试（无 mock，无网络）
# ---------------------------------------------------------------------------

class TestToBase64Url:
    """_to_base64_url 生成正确 data URI"""

    def test_png_file(self, tmp_path):
        """PNG 文件生成正确 data URI"""
        png_path = tmp_path / "test.png"
        png_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        png_path.write_bytes(png_data)

        result = ImageWorker._to_base64_url(str(png_path))

        assert result.startswith("data:image/png;base64,")
        # 验证 base64 部分可以解码
        b64_part = result.split(",", 1)[1]
        decoded = base64.b64decode(b64_part)
        assert decoded == png_data

    def test_jpeg_file(self, tmp_path):
        """JPEG 文件生成正确 data URI"""
        jpg_path = tmp_path / "test.jpg"
        jpg_data = b"\xff\xd8\xff\xe0" + b"\x00" * 50
        jpg_path.write_bytes(jpg_data)

        result = ImageWorker._to_base64_url(str(jpg_path))

        assert result.startswith("data:image/jpeg;base64,")

    def test_unknown_extension(self, tmp_path):
        """未知扩展名默认 image/png"""
        unknown_path = tmp_path / "test.xyz"
        unknown_path.write_bytes(b"some data")

        result = ImageWorker._to_base64_url(str(unknown_path))

        # mimetypes 可能返回 None，代码默认 image/png
        assert "base64," in result


class TestIsAdImage:
    """_is_ad_image 各类广告/装饰图片过滤"""

    def setup_method(self):
        # 使用 mock_settings 需要 BaseWorker 可初始化，这里直接绕过
        self.worker = object.__new__(ImageWorker)

    def test_qrcode_url_filtered(self):
        assert self.worker._is_ad_image(
            "https://example.com/qrcode.png",
            {"alt": ""}
        ) is True

    def test_reward_url_filtered(self):
        assert self.worker._is_ad_image(
            "https://example.com/reward-button.png",
            {"alt": ""}
        ) is True

    def test_donate_url_filtered(self):
        assert self.worker._is_ad_image(
            "https://example.com/donate_me.png",
            {"alt": ""}
        ) is True

    def test_sponsor_url_filtered(self):
        assert self.worker._is_ad_image(
            "https://example.com/sponsor-logo.png",
            {"alt": ""}
        ) is True

    def test_ad_prefix_filtered(self):
        assert self.worker._is_ad_image(
            "https://example.com/ad_banner.jpg",
            {"alt": ""}
        ) is True

    def test_banner_url_filtered(self):
        assert self.worker._is_ad_image(
            "https://example.com/banner.jpg",
            {"alt": ""}
        ) is True

    def test_tracking_url_filtered(self):
        assert self.worker._is_ad_image(
            "https://example.com/tracking-pixel.gif",
            {"alt": ""}
        ) is True

    def test_icon_alt_filtered(self):
        assert self.worker._is_ad_image(
            "https://example.com/img.png",
            {"alt": "GitHub icon"}
        ) is True

    def test_logo_alt_filtered(self):
        assert self.worker._is_ad_image(
            "https://example.com/img.png",
            {"alt": "Company logo"}
        ) is True

    def test_badge_alt_filtered(self):
        assert self.worker._is_ad_image(
            "https://example.com/img.png",
            {"alt": "CI badge"}
        ) is True

    def test_shield_alt_filtered(self):
        assert self.worker._is_ad_image(
            "https://example.com/img.png",
            {"alt": "shield status"}
        ) is True

    def test_wechat_gif_filtered(self):
        assert self.worker._is_ad_image(
            "https://mmbiz.qpic.cn/image.gif",
            {"alt": ""}
        ) is True

    def test_normal_image_not_filtered(self):
        """正常内容图片不误过滤"""
        assert self.worker._is_ad_image(
            "https://example.com/architecture-diagram.png",
            {"alt": "System Architecture"}
        ) is False

    def test_normal_photo_not_filtered(self):
        assert self.worker._is_ad_image(
            "https://cdn.example.com/photo-2024.jpg",
            {"alt": "Conference photo"}
        ) is False

    def test_data_visualization_not_filtered(self):
        assert self.worker._is_ad_image(
            "https://example.com/charts/performance.png",
            {"alt": "Performance comparison chart"}
        ) is False


class TestSvgFiltering:
    """SVG 文件应被跳过"""

    def setup_method(self):
        self.worker = object.__new__(ImageWorker)
        self.worker.browser = MagicMock()

    def test_svg_url_skipped(self):
        """.svg URL 被跳过，不调用 download"""
        input_data = MagicMock()
        input_data.extra = {
            "images": [
                {"url": "https://example.com/diagram.svg", "alt": "diagram"},
            ],
            "save_dir": "/tmp/imgs",
            "interpret": False,
        }

        result = self.worker.execute(input_data)

        assert result.data["images"] == []
        self.worker.browser.download_image.assert_not_called()

    def test_svg_with_query_string_skipped(self):
        """.svg?xxx URL 被跳过"""
        input_data = MagicMock()
        input_data.extra = {
            "images": [
                {"url": "https://example.com/icon.svg?v=2", "alt": "icon"},
            ],
            "save_dir": "/tmp/imgs",
            "interpret": False,
        }

        result = self.worker.execute(input_data)

        assert result.data["images"] == []
        self.worker.browser.download_image.assert_not_called()


class TestModelLevel:
    """model_level 配置断言"""

    def test_deep_model_level(self, mock_settings):
        """ImageWorker 应使用 deep 级别模型"""
        worker = ImageWorker()
        assert worker.spec.model_level == "deep"
        assert worker.get_model() == "test-deep"
