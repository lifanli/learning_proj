from github import Github, GithubException
import os
import re
from src.utils.logger import logger
from dotenv import load_dotenv

load_dotenv()

# 关键文件识别模式
_KEY_FILE_PATTERNS = [
    # 配置/项目文件
    r"^(setup\.py|setup\.cfg|pyproject\.toml|Cargo\.toml|package\.json|go\.mod)$",
    # 入口文件
    r"^(main|app|index|server|cli)\.(py|js|ts|go|rs)$",
    r"^src/(main|app|index|lib)\.(py|js|ts|go|rs)$",
    # 核心模块
    r"^(src|lib|pkg)/(core|engine|model|agent|pipeline)",
    # 文档
    r"^(ARCHITECTURE|DESIGN|CONTRIBUTING)\.(md|rst|txt)$",
]

_SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".tox", ".eggs",
    "dist", "build", ".next", "vendor", "venv", ".venv",
}

_BINARY_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".woff", ".woff2",
    ".ttf", ".eot", ".mp3", ".mp4", ".zip", ".tar", ".gz", ".bin",
    ".pyc", ".pyo", ".so", ".dll", ".exe", ".class", ".jar",
}


class GitHubAPI:
    def __init__(self):
        # Optional: Use token if available to increase rate limits
        self.token = os.getenv("GITHUB_TOKEN")
        if self.token:
            self.client = Github(self.token)
        else:
            self.client = Github() # Anonymous access (lower limits)

    def _parse_repo_name(self, repo_url: str) -> str:
        """从URL提取 owner/repo"""
        if "github.com/" not in repo_url:
            return ""
        parts = repo_url.split("github.com/")[-1].strip("/").split("/")
        if len(parts) < 2:
            return ""
        # 去掉可能的 .git 后缀和额外路径
        repo = parts[1].replace(".git", "")
        return f"{parts[0]}/{repo}"

    def get_repo_content(self, repo_url: str) -> dict:
        """
        Given a GitHub URL (e.g., https://github.com/owner/repo), fetch README and structure.
        """
        try:
            repo_name = self._parse_repo_name(repo_url)
            if not repo_name:
                return {}

            repo = self.client.get_repo(repo_name)

            content = {
                "name": repo.name,
                "description": repo.description,
                "stars": repo.stargazers_count,
                "language": repo.language,
                "readme": "",
                "structure": []
            }

            # Get README
            try:
                readme = repo.get_readme()
                content["readme"] = readme.decoded_content.decode("utf-8")
            except Exception:
                logger.warning(f"No README found for {repo_name}")

            # Get file structure (top level)
            try:
                contents = repo.get_contents("")
                content["structure"] = [c.path for c in contents]
            except Exception:
                pass

            return content

        except Exception as e:
            logger.error(f"Error fetching GitHub repo {repo_url}: {e}")
            return {}

    def get_repo_deep(self, repo_url: str, max_files: int = 15) -> dict:
        """
        深度读取GitHub仓库：README + 关键源码文件内容 + 完整目录树。

        返回:
        {
            "name": str,
            "description": str,
            "stars": int,
            "language": str,
            "readme": str,
            "structure": [str],        # 完整目录树
            "key_files": [             # 关键文件内容
                {"path": str, "content": str, "size": int}
            ],
            "topics": [str],           # 仓库标签
        }
        """
        try:
            repo_name = self._parse_repo_name(repo_url)
            if not repo_name:
                return {}

            repo = self.client.get_repo(repo_name)

            result = {
                "name": repo.name,
                "description": repo.description or "",
                "stars": repo.stargazers_count,
                "language": repo.language or "",
                "readme": "",
                "structure": [],
                "key_files": [],
                "topics": list(repo.get_topics()),
            }

            # 1. README
            try:
                readme = repo.get_readme()
                result["readme"] = readme.decoded_content.decode("utf-8")
            except Exception:
                logger.warning(f"No README found for {repo_name}")

            # 2. 递归获取目录树
            tree_items = self._get_full_tree(repo)
            result["structure"] = [item.path for item in tree_items]

            # 3. 识别并读取关键文件
            key_paths = self._identify_key_files(tree_items, repo.language)
            for path in key_paths[:max_files]:
                content = self._read_file_content(repo, path)
                if content is not None:
                    result["key_files"].append({
                        "path": path,
                        "content": content,
                        "size": len(content),
                    })

            logger.info(
                f"GitHub深度分析: {repo_name} | "
                f"树={len(result['structure'])}文件, "
                f"关键文件={len(result['key_files'])}"
            )
            return result

        except Exception as e:
            logger.error(f"GitHub深度读取失败 {repo_url}: {e}")
            return self.get_repo_content(repo_url)  # 降级到浅读

    def _get_full_tree(self, repo) -> list:
        """获取仓库完整目录树（使用Git Tree API，单次请求）"""
        try:
            tree = repo.get_git_tree(sha="HEAD", recursive=True)
            return [item for item in tree.tree if item.type == "blob"]
        except Exception as e:
            logger.warning(f"获取目录树失败，降级到顶层: {e}")
            try:
                contents = repo.get_contents("")
                return contents
            except Exception:
                return []

    def _identify_key_files(self, tree_items, language: str = "") -> list:
        """
        从目录树中识别关键文件。
        优先级：入口文件 > 核心模块 > 配置文件
        """
        candidates = []

        for item in tree_items:
            path = item.path
            ext = os.path.splitext(path)[1].lower()

            # 跳过二进制和过大文件
            if ext in _BINARY_EXTS:
                continue
            if hasattr(item, "size") and item.size and item.size > 100_000:
                continue

            # 跳过不需要的目录下的文件
            parts = path.split("/")
            if any(p in _SKIP_DIRS for p in parts):
                continue

            score = 0
            for pattern in _KEY_FILE_PATTERNS:
                if re.match(pattern, path, re.IGNORECASE):
                    score += 10
                    break

            # 入口文件加分
            basename = os.path.basename(path)
            if basename in ("main.py", "app.py", "index.ts", "index.js", "main.go", "main.rs"):
                score += 15
            elif basename in ("setup.py", "pyproject.toml", "Cargo.toml", "package.json"):
                score += 8

            # 浅层文件加分
            depth = len(parts) - 1
            if depth <= 1:
                score += 5
            elif depth == 2:
                score += 2

            # src目录下加分
            if parts[0] in ("src", "lib", "pkg", "core"):
                score += 3

            if score > 0:
                candidates.append((score, path))

        # 按分数排序
        candidates.sort(key=lambda x: -x[0])
        return [path for _, path in candidates]

    def _read_file_content(self, repo, path: str, max_size: int = 50_000) -> str:
        """读取单个文件内容"""
        try:
            file_content = repo.get_contents(path)
            if file_content.size > max_size:
                logger.debug(f"文件过大，跳过: {path} ({file_content.size} bytes)")
                return None
            return file_content.decoded_content.decode("utf-8")
        except Exception as e:
            logger.debug(f"读取文件失败 {path}: {e}")
            return None

    def search_repo(self, query: str) -> str:
        """
        Search for a repository and return the URL of the top result.
        """
        try:
            repos = self.client.search_repositories(query=query, sort="stars", order="desc")
            if repos.totalCount > 0:
                return repos[0].html_url
            return ""
        except Exception as e:
            logger.error(f"Error searching GitHub: {e}")
            return ""
