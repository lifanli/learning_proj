"""
test_web_browser.py — WebBrowser (BeautifulSoup) 测试
"""

import os
from unittest.mock import patch, MagicMock
import pytest

from src.tools.web_browser import WebBrowser


# ---------------------------------------------------------------------------
# 纯逻辑测试（无 mock，无网络）
# ---------------------------------------------------------------------------

class TestExtractText:
    """extract_text 去除 script/style/nav/footer"""

    def test_strips_unwanted_tags(self, sample_html):
        browser = WebBrowser()
        text = browser.extract_text(sample_html)
        assert "Navigation bar" not in text
        assert "Footer content" not in text
        assert "var x = 1" not in text
        assert ".hidden{display:none}" not in text

    def test_preserves_content_text(self, sample_html):
        browser = WebBrowser()
        text = browser.extract_text(sample_html)
        assert "Main Title" in text
        assert "Introduction paragraph" in text
        assert "Some text content here" in text

    def test_empty_html(self):
        browser = WebBrowser()
        text = browser.extract_text("")
        assert text == ""

    def test_plain_text_html(self):
        browser = WebBrowser()
        text = browser.extract_text("<p>Hello World</p>")
        assert "Hello World" in text


class TestExtractContentWithImages:
    """extract_content_with_images 提取图片/代码块/标题，相对 URL 解析"""

    def test_extracts_images(self, sample_html):
        browser = WebBrowser()
        result = browser.extract_content_with_images(sample_html, base_url="https://example.com")

        assert len(result["images"]) == 2
        # 相对 URL 应该被解析为绝对 URL
        assert result["images"][0]["url"] == "https://example.com/images/diagram.png"
        assert result["images"][0]["alt"] == "Architecture diagram"
        # 绝对 URL 保持不变
        assert result["images"][1]["url"] == "https://example.com/photo.jpg"

    def test_extracts_code_blocks(self, sample_html):
        browser = WebBrowser()
        result = browser.extract_content_with_images(sample_html)

        assert len(result["code_blocks"]) == 1
        assert result["code_blocks"][0]["language"] == "python"
        assert 'print("hello world")' in result["code_blocks"][0]["code"]

    def test_extracts_headings(self, sample_html):
        browser = WebBrowser()
        result = browser.extract_content_with_images(sample_html)

        heading_texts = [h["text"] for h in result["headings"]]
        assert "Main Title" in heading_texts
        assert "Section One" in heading_texts
        assert "Sub Section" in heading_texts

        levels = {h["text"]: h["level"] for h in result["headings"]}
        assert levels["Main Title"] == 1
        assert levels["Section One"] == 2
        assert levels["Sub Section"] == 3

    def test_image_placeholder_in_text(self, sample_html):
        browser = WebBrowser()
        result = browser.extract_content_with_images(sample_html, base_url="https://example.com")
        assert "[IMAGE_0:" in result["text"]

    def test_no_base_url_relative_images(self):
        """不提供 base_url 时，相对路径图片 src 保持原样"""
        html = '<article><img src="/img/test.png" alt="test"></article>'
        browser = WebBrowser()
        result = browser.extract_content_with_images(html)
        assert result["images"][0]["url"] == "/img/test.png"


class TestExtractLinks:
    """extract_links 过滤 #/javascript:/mailto:"""

    def test_filters_anchor_links(self, sample_html):
        browser = WebBrowser()
        links = browser.extract_links(sample_html, "https://example.com")
        hrefs = links
        # 应该包含 /docs/page 解析后的绝对路径
        assert "https://example.com/docs/page" in hrefs
        # 不应包含纯锚点链接
        for link in hrefs:
            assert not link.startswith("#")
            assert "javascript:" not in link
            assert "mailto:" not in link

    def test_resolves_relative_urls(self):
        html = '<a href="/path/page">Link</a>'
        browser = WebBrowser()
        links = browser.extract_links(html, "https://example.com")
        assert "https://example.com/path/page" in links

    def test_empty_html_returns_empty(self):
        browser = WebBrowser()
        links = browser.extract_links("", "https://example.com")
        assert links == []

    def test_deduplicates_links(self):
        html = '<a href="/page">A</a><a href="/page">B</a>'
        browser = WebBrowser()
        links = browser.extract_links(html, "https://example.com")
        assert links.count("https://example.com/page") == 1


# ---------------------------------------------------------------------------
# Mock 单元测试
# ---------------------------------------------------------------------------

class TestFetchPageMock:
    """Mock requests 测试 fetch_page"""

    @patch("src.tools.web_browser.requests")
    def test_fetch_page_success(self, mock_requests):
        mock_response = MagicMock()
        mock_response.text = "<html><body>Hello</body></html>"
        mock_response.raise_for_status = MagicMock()
        mock_requests.get.return_value = mock_response

        browser = WebBrowser()
        html = browser.fetch_page("https://example.com")
        assert "Hello" in html

    @patch("src.tools.web_browser.requests")
    def test_fetch_page_failure(self, mock_requests):
        mock_requests.get.side_effect = Exception("Connection timeout")

        browser = WebBrowser()
        html = browser.fetch_page("https://example.com")
        assert html == ""


class TestDownloadImageMock:
    """Mock requests 测试 download_image"""

    @patch("src.tools.web_browser.requests")
    def test_download_image_content_type_check(self, mock_requests, tmp_path):
        """Content-Type 非图片 → 返回空字符串"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.headers = {"Content-Type": "text/html"}
        mock_requests.get.return_value = mock_response

        browser = WebBrowser()
        result = browser.download_image("https://example.com/not-image", str(tmp_path))
        assert result == ""

    @patch("src.tools.web_browser.requests")
    def test_download_image_success(self, mock_requests, tmp_path):
        """正常图片下载"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.headers = {"Content-Type": "image/png"}
        mock_response.iter_content.return_value = [b"fake png data"]
        mock_requests.get.return_value = mock_response

        browser = WebBrowser()
        result = browser.download_image("https://example.com/img.png", str(tmp_path))
        assert result != ""
        assert os.path.exists(result)

    @patch("src.tools.web_browser.requests")
    def test_download_image_already_cached(self, mock_requests, tmp_path):
        """文件已存在 → 跳过下载，直接返回路径"""
        import hashlib
        url = "https://example.com/cached.png"
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        cached_file = tmp_path / f"{url_hash}.png"
        cached_file.write_bytes(b"cached")

        browser = WebBrowser()
        result = browser.download_image(url, str(tmp_path))
        assert result == str(cached_file)
        mock_requests.get.assert_not_called()


# ---------------------------------------------------------------------------
# 集成冒烟测试
# ---------------------------------------------------------------------------

@pytest.mark.slow
class TestWebBrowserIntegration:

    def test_real_fetch_and_extract(self):
        browser = WebBrowser()
        html = browser.fetch_page("https://example.com")
        if html:
            text = browser.extract_text(html)
            assert len(text) > 0
