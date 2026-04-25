"""
主题资源探索器 (TopicExplorer)
================================
给定一个主题，通过多渠道搜索发现学习资源。

搜索渠道：
1. CurriculumRegistry 预置优质源（精确匹配）
2. DuckDuckGo Web搜索（教程、文档）
3. GitHub 仓库搜索（高星项目）
4. ArXiv 论文搜索（最新研究）

输出：去重、排序后的资源列表，带类型和优先级。
"""

import re
import yaml
from typing import List, Dict
from urllib.parse import urlparse

from src.tools.web_search import WebSearch
from src.tools.github_api import GitHubAPI
from src.researchers.arxiv_researcher import ArxivResearcher
from src.utils.logger import logger

REGISTRY_PATH = "config/curriculum_registry.yaml"


class TopicExplorer:
    """主题资源探索器"""

    def __init__(self):
        self.web_search = WebSearch()
        self.github = GitHubAPI()
        self.arxiv = ArxivResearcher()
        self.registry = self._load_registry()

    def _load_registry(self) -> List[Dict]:
        try:
            with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return data.get("sources", [])
        except Exception:
            return []

    def explore(
        self,
        topic: str,
        search_queries: List[str] = None,
        max_results: int = 10,
        channels: List[str] = None,
    ) -> List[Dict]:
        """
        搜索某主题的学习资源。

        Args:
            topic: 主题名称
            search_queries: 额外搜索关键词列表
            max_results: 最终返回的最大结果数
            channels: 使用的搜索渠道，默认全部
                      可选值: "registry", "web", "github", "arxiv"

        Returns:
            [{url, title, type, source_channel, relevance_score}]
        """
        if channels is None:
            channels = ["registry", "web", "github", "arxiv"]

        all_queries = [topic]
        if search_queries:
            all_queries.extend(search_queries)

        results = []

        # 1. 预置源匹配
        if "registry" in channels:
            results.extend(self._search_registry(topic, all_queries))

        # 2. Web搜索
        if "web" in channels:
            results.extend(self._search_web(all_queries))

        # 3. GitHub搜索
        if "github" in channels:
            results.extend(self._search_github(topic, all_queries))

        # 4. ArXiv搜索
        if "arxiv" in channels:
            results.extend(self._search_arxiv(topic, all_queries))

        # 去重 + 排序
        results = self._deduplicate(results)
        results.sort(key=lambda x: -x.get("relevance_score", 0))

        logger.info(
            f"[TopicExplorer] 主题 '{topic}' 找到 {len(results)} 个资源 "
            f"(返回前 {max_results} 个)"
        )
        return results[:max_results]

    @staticmethod
    def _has_chinese(text: str) -> bool:
        """判断文本是否包含中文字符"""
        return bool(re.search(r'[\u4e00-\u9fff]', text))

    def _get_english_queries(self, queries: List[str]) -> List[str]:
        """从 queries 中提取英文查询（不含中文的），保持顺序"""
        return [q for q in queries if not self._has_chinese(q)]

    def _get_chinese_queries(self, queries: List[str]) -> List[str]:
        """从 queries 中提取中文查询（包含中文字符的），保持顺序"""
        return [q for q in queries if self._has_chinese(q)]

    def _search_registry(self, topic: str, queries: List[str]) -> List[Dict]:
        """从预置注册表匹配"""
        results = []
        topic_lower = " ".join(queries).lower()

        for source in self.registry:
            keywords = source.get("keywords", [])
            matched_count = sum(
                1 for kw in keywords if kw.lower() in topic_lower
            )
            if matched_count > 0:
                results.append({
                    "url": source["url"],
                    "title": source["name"],
                    "type": source.get("type", "doc"),
                    "source_channel": "registry",
                    "relevance_score": 100 + matched_count * 10,  # 预置源高优先级
                })

        return results

    def _search_web(self, queries: List[str]) -> List[Dict]:
        """DuckDuckGo Web 搜索（中英双语）"""
        results = []
        en_queries = self._get_english_queries(queries)
        cn_queries = self._get_chinese_queries(queries)
        search_terms = []

        # 英文搜索词优先：主要高质量技术资料来源仍然是英文
        if en_queries:
            search_terms.append(f"{en_queries[0]} tutorial documentation")
            if len(en_queries) > 1:
                search_terms.append(f"{en_queries[1]} guide")

        # 只有在没有英文 query 时，才回退到中文搜索词
        if not en_queries and cn_queries:
            search_terms.append(f"{cn_queries[0]} 教程 文档")

        # 没有任何中英文 query 时 fallback
        if not en_queries and not cn_queries:
            search_terms.append(f"{queries[0]} tutorial documentation")

        for term in search_terms[:3]:
            try:
                hits = self.web_search.search(term, max_results=5)
                for hit in hits:
                    url = hit.get("href", "")
                    if not url:
                        continue
                    if self._is_low_quality_url(url):
                        continue
                    results.append({
                        "url": url,
                        "title": hit.get("title", ""),
                        "type": self._detect_url_type(url),
                        "source_channel": "web",
                        "relevance_score": 50,
                    })
            except Exception as e:
                logger.warning(f"[TopicExplorer] Web搜索失败 '{term}': {e}")

        return results

    def _search_github(self, topic: str, queries: List[str]) -> List[Dict]:
        """GitHub 仓库搜索（英文为主，中文补充）"""
        results = []
        en_queries = self._get_english_queries(queries)
        cn_queries = self._get_chinese_queries(queries)

        # 英文主搜索
        search_term = en_queries[0] if en_queries else topic
        try:
            repos = self.github.client.search_repositories(
                query=search_term, sort="stars", order="desc"
            )
            for i, repo in enumerate(repos):
                if i >= 5:
                    break
                results.append({
                    "url": repo.html_url,
                    "title": f"{repo.full_name} ({repo.stargazers_count} stars)",
                    "type": "github",
                    "source_channel": "github",
                    "relevance_score": min(70, 30 + repo.stargazers_count // 1000),
                })
        except Exception as e:
            logger.warning(f"[TopicExplorer] GitHub搜索失败 '{search_term}': {e}")

        # 中文补充搜索仅在没有英文 query 时启用，避免把英文主搜索结果覆盖成中文 fallback
        if cn_queries and not en_queries:
            cn_term = cn_queries[0]
            try:
                repos = self.github.client.search_repositories(
                    query=cn_term, sort="stars", order="desc"
                )
                for i, repo in enumerate(repos):
                    if i >= 3:
                        break
                    results.append({
                        "url": repo.html_url,
                        "title": f"{repo.full_name} ({repo.stargazers_count} stars)",
                        "type": "github",
                        "source_channel": "github",
                        "relevance_score": min(65, 25 + repo.stargazers_count // 1000),
                    })
            except Exception as e:
                logger.warning(f"[TopicExplorer] GitHub中文搜索失败 '{cn_term}': {e}")

        return results

    def _search_arxiv(self, topic: str, queries: List[str]) -> List[Dict]:
        """ArXiv 论文搜索"""
        results = []
        # ArXiv以英文为主，优先用英文query搜索
        en_queries = self._get_english_queries(queries)
        search_term = en_queries[0] if en_queries else topic
        try:
            papers = self.arxiv.search_papers(search_term, max_results=3)
            for paper in papers:
                results.append({
                    "url": paper.get("entry_id", ""),
                    "title": paper.get("title", ""),
                    "type": "arxiv",
                    "source_channel": "arxiv",
                    "relevance_score": 60,
                })
        except Exception as e:
            logger.warning(f"[TopicExplorer] ArXiv搜索失败 '{topic}': {e}")

        return results

    def _deduplicate(self, results: List[Dict]) -> List[Dict]:
        """URL去重，保留高分的"""
        seen = {}
        for r in results:
            url = self._normalize_url(r.get("url", ""))
            if not url:
                continue
            if url not in seen or r.get("relevance_score", 0) > seen[url].get("relevance_score", 0):
                seen[url] = r
        return list(seen.values())

    def _normalize_url(self, url: str) -> str:
        """URL标准化"""
        url = url.rstrip("/").split("#")[0].split("?")[0]
        return url

    def _is_low_quality_url(self, url: str) -> bool:
        """过滤低质量URL"""
        low_quality_domains = {
            "youtube.com", "twitter.com", "x.com", "facebook.com",
            "reddit.com", "medium.com", "readmedium.com",
            "stackoverflow.com",
        }
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        return domain in low_quality_domains

    def _detect_url_type(self, url: str) -> str:
        """检测URL类型"""
        if "github.com" in url:
            return "github"
        elif "arxiv.org" in url:
            return "arxiv"
        elif any(kw in url for kw in ("docs.", "documentation", "readthedocs", "/docs/")):
            return "doc"
        elif any(kw in url for kw in ("learn", "course", "tutorial")):
            return "course"
        else:
            return "web"
