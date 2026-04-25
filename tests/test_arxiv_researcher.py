"""
test_arxiv_researcher.py — ArxivResearcher 测试
"""

import os
from unittest.mock import patch, MagicMock
from datetime import datetime
import pytest

from src.researchers.arxiv_researcher import ArxivResearcher


# ---------------------------------------------------------------------------
# Mock 单元测试
# ---------------------------------------------------------------------------

class TestSearchPapersMock:
    """Mock arxiv 库测试 search_papers"""

    def _make_mock_result(self, title="Paper Title", arxiv_id="2401.00001"):
        result = MagicMock()
        result.title = title
        result.authors = [MagicMock(name="Author A"), MagicMock(name="Author B")]
        result.summary = "This paper presents..."
        result.published = datetime(2024, 1, 15)
        result.pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"
        result.entry_id = f"https://arxiv.org/abs/{arxiv_id}"
        result.categories = ["cs.AI", "cs.CL"]
        return result

    @patch("src.researchers.arxiv_researcher.arxiv")
    def test_search_papers_field_completeness(self, mock_arxiv, tmp_path):
        """验证返回字段完整性"""
        mock_result = self._make_mock_result()
        mock_client = MagicMock()
        mock_client.results.return_value = [mock_result]
        mock_arxiv.Client.return_value = mock_client
        mock_arxiv.Search = MagicMock()
        mock_arxiv.SortCriterion.SubmittedDate = "submittedDate"

        researcher = ArxivResearcher(download_dir=str(tmp_path / "pdfs"))
        papers = researcher.search_papers("transformers", max_results=1)

        assert len(papers) == 1
        paper = papers[0]
        assert "title" in paper
        assert "authors" in paper
        assert "summary" in paper
        assert "published" in paper
        assert "pdf_url" in paper
        assert "entry_id" in paper
        assert "categories" in paper
        assert paper["title"] == "Paper Title"
        assert paper["published"] == "2024-01-15"

    @patch("src.researchers.arxiv_researcher.arxiv")
    def test_fetch_daily_updates_query_format(self, mock_arxiv, tmp_path):
        """fetch_daily_updates 拼接 cat:cs.AI OR cat:cs.CL 查询"""
        mock_client = MagicMock()
        mock_client.results.return_value = []
        mock_arxiv.Client.return_value = mock_client
        mock_arxiv.Search = MagicMock()
        mock_arxiv.SortCriterion.SubmittedDate = "submittedDate"

        researcher = ArxivResearcher(download_dir=str(tmp_path / "pdfs"))
        researcher.fetch_daily_updates(categories=["cs.AI", "cs.CL"], max_results=5)

        # 验证 Search 被调用时的 query 包含 OR 连接
        call_args = mock_arxiv.Search.call_args
        query = call_args[1].get("query") or call_args[0][0] if call_args[0] else call_args[1]["query"]
        assert "cat:cs.AI" in query
        assert "OR" in query
        assert "cat:cs.CL" in query


class TestDownloadAndParseMock:
    """Mock 测试 download_and_parse"""

    @patch("src.researchers.arxiv_researcher.requests")
    @patch("src.researchers.arxiv_researcher.PDFParser")
    def test_download_failure_returns_empty(self, mock_parser, mock_requests, tmp_path):
        """下载失败（404）→ 返回 ''"""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_requests.get.return_value = mock_response

        with patch("src.researchers.arxiv_researcher.arxiv"):
            researcher = ArxivResearcher(download_dir=str(tmp_path / "pdfs"))

        result = researcher.download_and_parse("https://arxiv.org/pdf/9999.99999", "Fake Paper")
        assert result == ""

    @patch("src.researchers.arxiv_researcher.requests")
    @patch("src.researchers.arxiv_researcher.PDFParser")
    def test_cached_pdf_skips_download(self, mock_parser, mock_requests, tmp_path):
        """已缓存 PDF → 不重复下载"""
        download_dir = tmp_path / "pdfs"
        download_dir.mkdir()

        # 预先创建文件（模拟缓存）
        cached_path = download_dir / "Cached Paper.pdf"
        cached_path.write_bytes(b"fake pdf content")

        mock_parser.extract_text_from_pdf.return_value = "cached text"

        with patch("src.researchers.arxiv_researcher.arxiv"):
            researcher = ArxivResearcher(download_dir=str(download_dir))

        result = researcher.download_and_parse("https://arxiv.org/pdf/2401.00001", "Cached Paper")

        # requests.get 不应该被调用
        mock_requests.get.assert_not_called()
        assert result == "cached text"

    @patch("src.researchers.arxiv_researcher.requests")
    @patch("src.researchers.arxiv_researcher.PDFParser")
    def test_download_success_parses_pdf(self, mock_parser, mock_requests, tmp_path):
        """下载成功 → 解析 PDF 并返回文本"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"fake pdf bytes"
        mock_requests.get.return_value = mock_response

        mock_parser.extract_text_from_pdf.return_value = "parsed content"

        with patch("src.researchers.arxiv_researcher.arxiv"):
            researcher = ArxivResearcher(download_dir=str(tmp_path / "pdfs"))

        result = researcher.download_and_parse("https://arxiv.org/pdf/2401.00001", "New Paper")
        assert result == "parsed content"


# ---------------------------------------------------------------------------
# 集成冒烟测试
# ---------------------------------------------------------------------------

@pytest.mark.slow
class TestArxivResearcherIntegration:

    def test_real_search(self, tmp_path):
        researcher = ArxivResearcher(download_dir=str(tmp_path / "pdfs"))
        papers = researcher.search_papers("attention is all you need", max_results=1)
        assert isinstance(papers, list)
        if papers:
            assert "title" in papers[0]
