"""
test_topic_explorer.py — TopicExplorer (中英文路由) 测试
"""

from unittest.mock import patch, MagicMock
import pytest

from src.student.topic_explorer import TopicExplorer


# ---------------------------------------------------------------------------
# 纯逻辑测试（无 mock，无网络）
# ---------------------------------------------------------------------------

class TestHasChinese:
    """_has_chinese 中英文检测"""

    def test_pure_english(self):
        assert TopicExplorer._has_chinese("hello world") is False

    def test_pure_chinese(self):
        assert TopicExplorer._has_chinese("大语言模型") is True

    def test_mixed(self):
        assert TopicExplorer._has_chinese("LLM 大语言模型") is True

    def test_empty(self):
        assert TopicExplorer._has_chinese("") is False

    def test_numbers_and_symbols(self):
        assert TopicExplorer._has_chinese("GPT-4 v2.0") is False


class TestGetEnglishQueries:
    """_get_english_queries 过滤中文查询"""

    def setup_method(self):
        with patch.object(TopicExplorer, "__init__", lambda self: None):
            self.explorer = TopicExplorer()

    def test_filters_chinese_queries(self):
        queries = ["transformer", "大语言模型", "attention mechanism", "注意力机制"]
        result = self.explorer._get_english_queries(queries)
        assert result == ["transformer", "attention mechanism"]

    def test_all_english(self):
        queries = ["deep learning", "neural network"]
        result = self.explorer._get_english_queries(queries)
        assert result == ["deep learning", "neural network"]

    def test_all_chinese(self):
        queries = ["深度学习", "神经网络"]
        result = self.explorer._get_english_queries(queries)
        assert result == []

    def test_empty_list(self):
        result = self.explorer._get_english_queries([])
        assert result == []


class TestUrlHelpers:
    """URL 辅助方法测试"""

    def setup_method(self):
        with patch.object(TopicExplorer, "__init__", lambda self: None):
            self.explorer = TopicExplorer()

    def test_normalize_url_strips_trailing_slash(self):
        assert self.explorer._normalize_url("https://example.com/") == "https://example.com"

    def test_normalize_url_strips_fragment(self):
        assert self.explorer._normalize_url("https://example.com/page#section") == "https://example.com/page"

    def test_normalize_url_strips_query(self):
        assert self.explorer._normalize_url("https://example.com/page?key=val") == "https://example.com/page"

    def test_is_low_quality_url(self):
        assert self.explorer._is_low_quality_url("https://www.youtube.com/watch?v=123") is True
        assert self.explorer._is_low_quality_url("https://reddit.com/r/python") is True
        assert self.explorer._is_low_quality_url("https://docs.python.org/3/") is False

    def test_detect_url_type_github(self):
        assert self.explorer._detect_url_type("https://github.com/owner/repo") == "github"

    def test_detect_url_type_arxiv(self):
        assert self.explorer._detect_url_type("https://arxiv.org/abs/2401.00001") == "arxiv"

    def test_detect_url_type_doc(self):
        assert self.explorer._detect_url_type("https://docs.python.org/3/") == "doc"

    def test_detect_url_type_course(self):
        assert self.explorer._detect_url_type("https://learn.microsoft.com/course") == "course"

    def test_detect_url_type_web(self):
        assert self.explorer._detect_url_type("https://example.com/page") == "web"


class TestDeduplicate:
    """去重保留高分"""

    def setup_method(self):
        with patch.object(TopicExplorer, "__init__", lambda self: None):
            self.explorer = TopicExplorer()

    def test_keeps_higher_score(self):
        results = [
            {"url": "https://a.com/page", "title": "Low", "relevance_score": 10},
            {"url": "https://a.com/page", "title": "High", "relevance_score": 90},
        ]
        deduped = self.explorer._deduplicate(results)
        assert len(deduped) == 1
        assert deduped[0]["title"] == "High"

    def test_different_urls_preserved(self):
        results = [
            {"url": "https://a.com", "relevance_score": 50},
            {"url": "https://b.com", "relevance_score": 50},
        ]
        deduped = self.explorer._deduplicate(results)
        assert len(deduped) == 2

    def test_empty_url_filtered(self):
        results = [
            {"url": "", "relevance_score": 100},
            {"url": "https://a.com", "relevance_score": 50},
        ]
        deduped = self.explorer._deduplicate(results)
        assert len(deduped) == 1


# ---------------------------------------------------------------------------
# Mock 渠道测试
# ---------------------------------------------------------------------------

class TestSearchChannelsMock:
    """Mock 各搜索渠道，测试路由逻辑"""

    def _make_explorer(self):
        """创建一个不执行 __init__ 的 TopicExplorer"""
        with patch.object(TopicExplorer, "__init__", lambda self: None):
            explorer = TopicExplorer()
        explorer.web_search = MagicMock()
        explorer.github = MagicMock()
        explorer.arxiv = MagicMock()
        explorer.registry = []
        return explorer

    def test_github_uses_english_query(self):
        """GitHub 搜索使用英文 query 而非中文 topic"""
        explorer = self._make_explorer()
        explorer.github.client.search_repositories.return_value = []

        explorer._search_github(
            topic="大语言模型",
            queries=["大语言模型", "large language model"]
        )

        call_args = explorer.github.client.search_repositories.call_args
        search_query = call_args[1].get("query") or call_args[0][0]
        # 应该使用英文 query
        assert search_query == "large language model"

    def test_github_falls_back_to_topic_when_no_english(self):
        """全中文时 GitHub 搜索 fallback 到中文 topic"""
        explorer = self._make_explorer()
        explorer.github.client.search_repositories.return_value = []

        explorer._search_github(
            topic="深度学习",
            queries=["深度学习", "神经网络"]
        )

        call_args = explorer.github.client.search_repositories.call_args
        search_query = call_args[1].get("query") or call_args[0][0]
        assert search_query == "深度学习"

    def test_web_search_prefers_english_queries(self):
        """有英文 query 时，web 搜索应优先只用英文搜索词"""
        explorer = self._make_explorer()
        explorer.web_search.search.return_value = []

        explorer._search_web(queries=["大语言模型", "large language model"])

        called_terms = [call.args[0] for call in explorer.web_search.search.call_args_list]
        assert called_terms
        assert all("大语言模型" not in term for term in called_terms)
        assert any("large language model" in term for term in called_terms)

    def test_web_search_fallback_to_chinese(self):
        """全中文时 web 搜索 fallback 到中文"""
        explorer = self._make_explorer()
        explorer.web_search.search.return_value = []

        explorer._search_web(queries=["深度学习", "神经网络"])

        # 应该有至少一次调用，且包含中文
        call_args = explorer.web_search.search.call_args_list[0]
        term = call_args[0][0]
        assert "深度学习" in term

    def test_channel_parameter_controls_search(self):
        """channels 参数控制哪些搜索渠道被调用"""
        explorer = self._make_explorer()
        explorer.web_search.search.return_value = []

        result = explorer.explore(
            topic="test",
            channels=["web"],
            max_results=5,
        )

        # web_search 应该被调用
        assert explorer.web_search.search.called
        # github 和 arxiv 不应被调用
        assert not explorer.github.client.search_repositories.called
        assert not explorer.arxiv.search_papers.called
