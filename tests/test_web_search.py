"""
test_web_search.py — WebSearch (DuckDuckGo) 测试
"""

from unittest.mock import patch, MagicMock
import pytest

from src.tools.web_search import WebSearch


# ---------------------------------------------------------------------------
# Mock 单元测试
# ---------------------------------------------------------------------------

class TestWebSearchMock:
    """使用 mock 测试 WebSearch，不发起真实网络请求"""

    def _make_ws(self, **kwargs):
        """创建 WebSearch 并跳过请求间延迟"""
        ws = WebSearch(**kwargs)
        ws._last_call_time = 0.0
        return ws

    @patch("src.tools.web_search.time")
    def test_search_returns_results(self, mock_time):
        """Mock DDGS 上下文管理器，测试正常返回"""
        mock_time.time.return_value = 100.0
        mock_time.sleep = MagicMock()

        fake_results = [
            {"title": "Result 1", "href": "https://a.com", "body": "desc1"},
            {"title": "Result 2", "href": "https://b.com", "body": "desc2"},
        ]

        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.text.return_value = fake_results
        mock_ddgs_instance.__enter__ = MagicMock(return_value=mock_ddgs_instance)
        mock_ddgs_instance.__exit__ = MagicMock(return_value=False)

        with patch("src.tools.web_search.DDGS", return_value=mock_ddgs_instance):
            ws = self._make_ws(max_results=5)
            results = ws.search("test query")

        assert len(results) == 2
        assert results[0]["title"] == "Result 1"
        assert results[1]["href"] == "https://b.com"

    @patch("src.tools.web_search.time")
    def test_search_respects_max_results_parameter(self, mock_time):
        """传入 max_results 参数覆盖默认值"""
        mock_time.time.return_value = 100.0
        mock_time.sleep = MagicMock()

        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.text.return_value = [{"title": "A", "href": "https://a.com", "body": ""}]
        mock_ddgs_instance.__enter__ = MagicMock(return_value=mock_ddgs_instance)
        mock_ddgs_instance.__exit__ = MagicMock(return_value=False)

        with patch("src.tools.web_search.DDGS", return_value=mock_ddgs_instance):
            ws = self._make_ws(max_results=10)
            ws.search("q", max_results=3)

        mock_ddgs_instance.text.assert_called_once_with("q", max_results=3)

    @patch("src.tools.web_search.time")
    def test_search_ratelimit_retries_then_fails(self, mock_time):
        """Ratelimit 异常 → 重试 3 次后返回 [] 不崩溃"""
        mock_time.time.return_value = 100.0
        mock_time.sleep = MagicMock()

        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.text.side_effect = Exception("202 Ratelimit")
        mock_ddgs_instance.__enter__ = MagicMock(return_value=mock_ddgs_instance)
        mock_ddgs_instance.__exit__ = MagicMock(return_value=False)

        with patch("src.tools.web_search.DDGS", return_value=mock_ddgs_instance):
            ws = self._make_ws(max_retries=3)
            results = ws.search("test")

        assert results == []
        # 应该重试了 3 次
        assert mock_ddgs_instance.text.call_count == 3

    @patch("src.tools.web_search.time")
    def test_search_ratelimit_recovers_on_retry(self, mock_time):
        """限流后重试成功"""
        mock_time.time.return_value = 100.0
        mock_time.sleep = MagicMock()

        fake_results = [{"title": "OK", "href": "https://ok.com", "body": ""}]

        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.text.side_effect = [
            Exception("202 Ratelimit"),
            fake_results,
        ]
        mock_ddgs_instance.__enter__ = MagicMock(return_value=mock_ddgs_instance)
        mock_ddgs_instance.__exit__ = MagicMock(return_value=False)

        with patch("src.tools.web_search.DDGS", return_value=mock_ddgs_instance):
            ws = self._make_ws(max_retries=3)
            results = ws.search("test")

        assert len(results) == 1
        assert results[0]["title"] == "OK"

    @patch("src.tools.web_search.time")
    def test_non_ratelimit_error_no_retry(self, mock_time):
        """非限流异常 → 不重试，直接返回 []"""
        mock_time.time.return_value = 100.0
        mock_time.sleep = MagicMock()

        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.text.side_effect = Exception("Connection refused")
        mock_ddgs_instance.__enter__ = MagicMock(return_value=mock_ddgs_instance)
        mock_ddgs_instance.__exit__ = MagicMock(return_value=False)

        with patch("src.tools.web_search.DDGS", return_value=mock_ddgs_instance):
            ws = self._make_ws(max_retries=3)
            results = ws.search("test")

        assert results == []
        # 非限流错误只调用 1 次
        assert mock_ddgs_instance.text.call_count == 1

    @patch("src.tools.web_search.time")
    def test_search_first_link_normal(self, mock_time):
        """search_first_link 正常返回第一个链接"""
        mock_time.time.return_value = 100.0
        mock_time.sleep = MagicMock()

        fake_results = [{"title": "R1", "href": "https://first.com", "body": ""}]

        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.text.return_value = fake_results
        mock_ddgs_instance.__enter__ = MagicMock(return_value=mock_ddgs_instance)
        mock_ddgs_instance.__exit__ = MagicMock(return_value=False)

        with patch("src.tools.web_search.DDGS", return_value=mock_ddgs_instance):
            ws = self._make_ws()
            link = ws.search_first_link("test")

        assert link == "https://first.com"

    @patch("src.tools.web_search.time")
    def test_search_first_link_empty(self, mock_time):
        """search_first_link 无结果 → 返回 None"""
        mock_time.time.return_value = 100.0
        mock_time.sleep = MagicMock()

        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.text.return_value = []
        mock_ddgs_instance.__enter__ = MagicMock(return_value=mock_ddgs_instance)
        mock_ddgs_instance.__exit__ = MagicMock(return_value=False)

        with patch("src.tools.web_search.DDGS", return_value=mock_ddgs_instance):
            ws = self._make_ws()
            link = ws.search_first_link("test")

        assert link is None


# ---------------------------------------------------------------------------
# 集成冒烟测试
# ---------------------------------------------------------------------------

@pytest.mark.slow
class TestWebSearchIntegration:
    """真实 API 调用（需网络），用 -m slow 运行"""

    def test_real_search(self):
        ws = WebSearch(max_results=2)
        results = ws.search("Python tutorial")
        # 只要不崩溃即可；限流时可能为空
        assert isinstance(results, list)

    def test_real_search_first_link(self):
        ws = WebSearch()
        link = ws.search_first_link("Python tutorial")
        # 可能限流返回 None
        assert link is None or link.startswith("http")
