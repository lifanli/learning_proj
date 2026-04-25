"""
test_github_api.py — GitHubAPI 测试
"""

import os
from unittest.mock import patch, MagicMock, PropertyMock
import pytest

from src.tools.github_api import GitHubAPI, _KEY_FILE_PATTERNS, _BINARY_EXTS, _SKIP_DIRS


# ---------------------------------------------------------------------------
# 纯逻辑测试（无 mock, 无网络）
# ---------------------------------------------------------------------------

class TestParseRepoName:
    """_parse_repo_name 各种 URL 格式"""

    def setup_method(self):
        with patch("src.tools.github_api.Github"):
            self.api = GitHubAPI()

    def test_standard_url(self):
        assert self.api._parse_repo_name("https://github.com/owner/repo") == "owner/repo"

    def test_url_with_trailing_slash(self):
        assert self.api._parse_repo_name("https://github.com/owner/repo/") == "owner/repo"

    def test_url_with_git_suffix(self):
        assert self.api._parse_repo_name("https://github.com/owner/repo.git") == "owner/repo"

    def test_url_with_extra_path(self):
        assert self.api._parse_repo_name("https://github.com/owner/repo/tree/main/src") == "owner/repo"

    def test_http_url(self):
        assert self.api._parse_repo_name("http://github.com/owner/repo") == "owner/repo"

    def test_non_github_url(self):
        assert self.api._parse_repo_name("https://gitlab.com/owner/repo") == ""

    def test_incomplete_url(self):
        assert self.api._parse_repo_name("https://github.com/owner") == ""

    def test_empty_string(self):
        assert self.api._parse_repo_name("") == ""


class TestIdentifyKeyFiles:
    """_identify_key_files 评分排序 + 过滤"""

    def setup_method(self):
        with patch("src.tools.github_api.Github"):
            self.api = GitHubAPI()

    def _make_item(self, path, size=1000):
        item = MagicMock()
        item.path = path
        item.size = size
        return item

    def test_entry_files_ranked_highest(self):
        items = [
            self._make_item("README.md"),
            self._make_item("src/utils.py"),
            self._make_item("main.py"),
            self._make_item("setup.py"),
        ]
        result = self.api._identify_key_files(items)
        # main.py 应该排在最前面（入口加分 15 + 浅层 5 + 模式匹配 10 = 30）
        assert result[0] == "main.py"

    def test_binary_files_filtered(self):
        items = [
            self._make_item("logo.png"),
            self._make_item("app.exe"),
            self._make_item("main.py"),
        ]
        result = self.api._identify_key_files(items)
        assert "logo.png" not in result
        assert "app.exe" not in result
        assert "main.py" in result

    def test_large_files_filtered(self):
        items = [
            self._make_item("huge_data.csv", size=200_000),
            self._make_item("main.py", size=5000),
        ]
        result = self.api._identify_key_files(items)
        assert "huge_data.csv" not in result

    def test_skip_dirs_filtered(self):
        items = [
            self._make_item("node_modules/package/index.js"),
            self._make_item("__pycache__/module.pyc"),
            self._make_item("src/core/engine.py"),
        ]
        result = self.api._identify_key_files(items)
        assert "node_modules/package/index.js" not in result

    def test_src_depth_bonus(self):
        """src 目录下的文件获得额外加分"""
        items = [
            self._make_item("src/core/engine.py"),
            self._make_item("docs/readme.txt"),
        ]
        result = self.api._identify_key_files(items)
        assert "src/core/engine.py" in result

    def test_empty_tree(self):
        assert self.api._identify_key_files([]) == []


# ---------------------------------------------------------------------------
# Mock 单元测试
# ---------------------------------------------------------------------------

class TestGetRepoContentMock:
    """Mock GitHub API 测试 get_repo_content"""

    def test_returns_repo_structure(self):
        with patch("src.tools.github_api.Github") as MockGithub:
            mock_repo = MagicMock()
            mock_repo.name = "requests"
            mock_repo.description = "HTTP library"
            mock_repo.stargazers_count = 50000
            mock_repo.language = "Python"

            mock_readme = MagicMock()
            mock_readme.decoded_content = b"# Requests\nHTTP for Humans"
            mock_repo.get_readme.return_value = mock_readme

            mock_file = MagicMock()
            mock_file.path = "setup.py"
            mock_repo.get_contents.return_value = [mock_file]

            MockGithub.return_value.get_repo.return_value = mock_repo

            api = GitHubAPI()
            result = api.get_repo_content("https://github.com/psf/requests")

        assert result["name"] == "requests"
        assert result["stars"] == 50000
        assert "Requests" in result["readme"]
        assert "setup.py" in result["structure"]

    def test_rate_limit_returns_empty(self):
        """403 rate limit → 返回 {}"""
        from github import GithubException

        with patch("src.tools.github_api.Github") as MockGithub:
            MockGithub.return_value.get_repo.side_effect = GithubException(
                403, {"message": "API rate limit exceeded"}, None
            )
            api = GitHubAPI()
            result = api.get_repo_content("https://github.com/psf/requests")

        assert result == {}

    def test_invalid_url_returns_empty(self):
        with patch("src.tools.github_api.Github"):
            api = GitHubAPI()
            result = api.get_repo_content("https://not-github.com/foo")
        assert result == {}


class TestGetRepoDeepMock:
    """Mock GitHub API 测试 get_repo_deep"""

    def test_exception_falls_back_to_get_repo_content(self):
        """get_repo_deep 异常 → 降级到 get_repo_content"""
        with patch("src.tools.github_api.Github") as MockGithub:
            mock_repo = MagicMock()
            mock_repo.name = "fallback"
            mock_repo.description = "desc"
            mock_repo.stargazers_count = 10
            mock_repo.language = "Python"
            mock_repo.get_topics.side_effect = Exception("API Error")

            mock_readme = MagicMock()
            mock_readme.decoded_content = b"# Fallback"
            mock_repo.get_readme.return_value = mock_readme
            mock_repo.get_contents.return_value = []

            MockGithub.return_value.get_repo.return_value = mock_repo

            api = GitHubAPI()
            result = api.get_repo_deep("https://github.com/owner/repo")

        # 降级后应该返回 get_repo_content 的结构
        assert result.get("name") == "fallback"


# ---------------------------------------------------------------------------
# 集成冒烟测试
# ---------------------------------------------------------------------------

@pytest.mark.slow
class TestGitHubAPIIntegration:
    """真实 API 调用（需网络 + 可能需要 GITHUB_TOKEN）"""

    def test_real_get_repo_content(self):
        api = GitHubAPI()
        result = api.get_repo_content("https://github.com/psf/requests")
        # 限流时可能返回 {}
        if result:
            assert result["name"] == "requests"
            assert len(result["readme"]) > 0
