"""
test_pdf_parser.py — PDFParser (PyMuPDF) 测试
"""

import pytest

from src.tools.pdf_parser import PDFParser


class TestExtractTextFromPdf:
    """测试 extract_text_from_pdf"""

    def test_real_pdf_extraction(self, minimal_pdf):
        """真实 PDF（fixture 生成）→ 提取文本"""
        text = PDFParser.extract_text_from_pdf(minimal_pdf)
        assert "Hello from test PDF" in text

    def test_multipage_pdf(self, multipage_pdf):
        """多页 PDF → 拼接所有页"""
        text = PDFParser.extract_text_from_pdf(multipage_pdf)
        assert "Page 1 content" in text
        assert "Page 2 content" in text
        assert "Page 3 content" in text

    def test_corrupt_pdf_returns_empty(self, corrupt_pdf):
        """损坏 PDF → 返回 "" 不崩溃"""
        text = PDFParser.extract_text_from_pdf(corrupt_pdf)
        assert text == ""

    def test_nonexistent_path_returns_empty(self):
        """不存在路径 → 返回 """""
        text = PDFParser.extract_text_from_pdf("/nonexistent/path/file.pdf")
        assert text == ""


class TestExtractTextFromStream:
    """测试 extract_text_from_stream"""

    def test_real_pdf_stream(self, minimal_pdf):
        """从 stream 提取文本"""
        with open(minimal_pdf, "rb") as f:
            data = f.read()
        text = PDFParser.extract_text_from_stream(data)
        assert "Hello from test PDF" in text

    def test_multipage_stream(self, multipage_pdf):
        """多页 PDF stream → 拼接所有页"""
        with open(multipage_pdf, "rb") as f:
            data = f.read()
        text = PDFParser.extract_text_from_stream(data)
        assert "Page 1 content" in text
        assert "Page 3 content" in text

    def test_corrupt_stream_returns_empty(self):
        """损坏的 stream → 返回 """""
        text = PDFParser.extract_text_from_stream(b"not a pdf at all")
        assert text == ""

    def test_empty_stream_returns_empty(self):
        """空 stream → 返回 """""
        text = PDFParser.extract_text_from_stream(b"")
        assert text == ""
