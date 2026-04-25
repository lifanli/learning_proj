"""
共享 pytest fixtures
"""

import os
import tempfile
import shutil

import pytest
import yaml


@pytest.fixture
def tmp_dir(tmp_path):
    """提供一个临时目录，测试结束后自动清理"""
    return tmp_path


@pytest.fixture
def minimal_pdf(tmp_path):
    """用 PyMuPDF 创建一个真实的 1 页 PDF，包含可提取文本"""
    import fitz

    pdf_path = tmp_path / "test.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Hello from test PDF")
    doc.save(str(pdf_path))
    doc.close()
    return str(pdf_path)


@pytest.fixture
def multipage_pdf(tmp_path):
    """多页 PDF，用于测试拼接"""
    import fitz

    pdf_path = tmp_path / "multipage.pdf"
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i + 1} content")
    doc.save(str(pdf_path))
    doc.close()
    return str(pdf_path)


@pytest.fixture
def corrupt_pdf(tmp_path):
    """截断的伪 PDF，测试错误处理"""
    pdf_path = tmp_path / "corrupt.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 this is not a real pdf")
    return str(pdf_path)


@pytest.fixture
def sample_html():
    """含图片、代码块、标题的 HTML"""
    return """<!DOCTYPE html>
<html>
<head><title>Test Page</title></head>
<body>
<nav>Navigation bar</nav>
<article>
  <h1>Main Title</h1>
  <p>Introduction paragraph.</p>
  <h2>Section One</h2>
  <p>Some text content here.</p>
  <img src="/images/diagram.png" alt="Architecture diagram">
  <pre><code class="language-python">print("hello world")</code></pre>
  <h3>Sub Section</h3>
  <p>More text with a <a href="/docs/page">link</a> and
     <a href="#anchor">anchor</a> and
     <a href="javascript:void(0)">js link</a> and
     <a href="mailto:a@b.com">email</a>.</p>
  <img src="https://example.com/photo.jpg" alt="Photo">
</article>
<footer>Footer content</footer>
<script>var x = 1;</script>
<style>.hidden{display:none}</style>
</body>
</html>"""


@pytest.fixture
def mock_settings(tmp_path, monkeypatch):
    """
    创建临时 config/settings.yaml 让 BaseWorker 初始化不报错。
    同时 monkeypatch 工作目录到 tmp_path，这样 BaseWorker._load_config()
    能读到这个 settings.yaml。
    """
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    settings = {
        "llm": {
            "api_key_env": "TEST_API_KEY",
            "base_url": "https://localhost/v1",
            "model": "test-model",
            "enable_thinking": False,
        },
        "models": {
            "fast": "test-fast",
            "deep": "test-deep",
            "vision": "test-vision",
        },
        "paths": {
            "knowledge_base": "knowledge_base",
            "data": "data",
            "materials": "data/materials",
        },
        "language": {
            "target": "Chinese",
            "translation_prompt": "Translate to Chinese.",
        },
        "student": {
            "max_concurrent_fetches": 2,
            "image_download": True,
            "image_interpret": False,
            "follow_references": False,
            "max_reference_depth": 1,
        },
        "publisher": {
            "min_section_words": 100,
            "max_section_words": 500,
            "include_code_annotations": True,
            "include_images": False,
            "quality_review": False,
        },
    }

    with open(config_dir / "settings.yaml", "w", encoding="utf-8") as f:
        yaml.dump(settings, f)

    monkeypatch.setenv("TEST_API_KEY", "fake-key-for-testing")
    monkeypatch.chdir(tmp_path)

    return settings
