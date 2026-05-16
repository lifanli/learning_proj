"""
学习计划管理器 (StudyPlanner)
=============================
分析输入URL/主题，制定学习计划，确定需要抓取的所有页面和任务。
"""

import re
from collections import deque
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from urllib.parse import unquote, urlparse, urlsplit, urlunsplit

from src.core.worker import BaseWorker, WorkerSpec, WorkerInput, WorkerOutput
from src.tools.web_browser import WebBrowser
from src.utils.logger import logger


@dataclass
class StudyPlan:
    """学习计划"""
    source_type: str = ""         # course, wechat, github, arxiv, doc
    root_url: str = ""
    title: str = ""
    pages: List[Dict] = field(default_factory=list)   # [{url, title, order}]
    github_urls: List[str] = field(default_factory=list)
    arxiv_urls: List[str] = field(default_factory=list)
    reference_urls: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


class StudyPlanner:
    """学习计划管理器"""

    ASSET_EXTENSIONS = (
        ".css", ".js", ".json", ".xml", ".rss", ".ico",
        ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg",
        ".zip", ".tar", ".gz", ".rar", ".7z",
        ".mp3", ".mp4", ".avi", ".mov", ".wmv",
    )
    LOW_VALUE_PATH_PARTS = (
        "/login", "/signin", "/sign-in", "/signup", "/sign-up",
        "/register", "/member", "/account", "/auth", "/logout",
        "/search", "/tag/", "/tags/", "/category/", "/categories/",
        "/privacy", "/terms", "/contact", "/about", "/pricing",
        "/jobs", "/careers", "/feed", "/rss", "/sitemap",
        "/wp-login", "/comment", "/comments", "/share",
    )
    CONTENT_PATH_HINTS = (
        "docs", "documentation", "guide", "tutorial", "learn",
        "course", "chapter", "lesson", "article", "blog", "post",
        "reference", "api", "concept", "architecture", "paper",
    )

    def __init__(self):
        self.browser = WebBrowser()

    def plan_course(self, url: str, max_pages: int = 50) -> StudyPlan:
        """制定课程学习计划：发现所有章节页面"""
        plan = StudyPlan(source_type="course", root_url=url)

        html = self.browser.fetch_page(url)
        if not html:
            logger.error(f"无法访问课程URL: {url}")
            return plan

        plan.title = self.browser.extract_title(html) or "在线课程"

        # 发现课程链接
        course_links = self.browser.discover_course_links(html, url)
        if not course_links:
            # 尝试从普通链接中筛选
            all_links = self.browser.extract_links(html, url)
            parsed_base = urlparse(url)
            course_links = [
                l for l in all_links
                if urlparse(l).netloc == parsed_base.netloc
                and urlparse(l).path.startswith(parsed_base.path)
                and l != url
            ]

        for i, link in enumerate(course_links[:max_pages]):
            plan.pages.append({
                "url": link,
                "title": "",    # 将在抓取时填充
                "order": i,
            })

        logger.info(f"课程学习计划: {plan.title} | {len(plan.pages)}个页面")
        return plan

    def plan_wechat(self, url: str) -> StudyPlan:
        """制定微信文章学习计划"""
        plan = StudyPlan(source_type="wechat", root_url=url)

        html = self.browser.fetch_page(url)
        if not html:
            return plan

        plan.title = self.browser.extract_title(html) or "微信文章"
        plan.pages.append({"url": url, "title": plan.title, "order": 0})

        # 从页面中发现GitHub/ArXiv链接
        plan.github_urls = self._find_github_urls(html)
        plan.arxiv_urls = self._find_arxiv_urls(html)

        logger.info(
            f"微信学习计划: {plan.title} | "
            f"GitHub={len(plan.github_urls)}, ArXiv={len(plan.arxiv_urls)}"
        )
        return plan

    def plan_github(self, url: str) -> StudyPlan:
        """制定GitHub仓库学习计划"""
        plan = StudyPlan(source_type="github", root_url=url)
        plan.github_urls = [url]
        plan.pages.append({"url": url, "title": "", "order": 0})
        return plan

    def plan_arxiv(self, url: str) -> StudyPlan:
        """制定ArXiv论文学习计划"""
        plan = StudyPlan(source_type="arxiv", root_url=url)
        plan.arxiv_urls = [url]
        plan.pages.append({"url": url, "title": "", "order": 0})
        return plan

    def plan_doc(self, url: str, max_pages: int = 20) -> StudyPlan:
        """制定文档学习计划"""
        plan = StudyPlan(source_type="doc", root_url=url)

        html = self.browser.fetch_page(url)
        if not html:
            return plan

        plan.title = self.browser.extract_title(html) or "技术文档"
        plan.pages.append({"url": url, "title": plan.title, "order": 0})

        # BFS发现相关页面
        all_links = self.browser.extract_links(html, url)
        parsed_base = urlparse(url)
        relevant = [
            l for l in all_links
            if urlparse(l).netloc == parsed_base.netloc
            and l != url
        ]

        for i, link in enumerate(relevant[:max_pages - 1]):
            plan.pages.append({
                "url": link,
                "title": "",
                "order": i + 1,
            })

        return plan

    def plan_web_site(
        self,
        url: str,
        max_pages: int = 8,
        max_depth: int = 1,
        min_content_chars: int = 200,
        topic: str = "",
        source_type: str = "web",
    ) -> StudyPlan:
        """
        制定普通网页/文档的多页面学习计划。

        根页既可能是文章正文，也可能只是导航页；因此这里会先用根页发现同站子页，
        再只把正文足够、非登录/搜索/导航类的页面加入学习计划。
        """
        plan = StudyPlan(source_type=source_type, root_url=url)
        max_pages = max(1, int(max_pages or 1))
        max_depth = max(0, int(max_depth or 0))
        min_content_chars = max(0, int(min_content_chars or 0))

        root_url = self._normalize_url(url)
        queue = deque([(root_url, 0)])
        queued = {root_url}
        visited = set()
        topic_terms = self._topic_terms(topic)

        # 页面质量过滤后可能丢掉入口页，所以抓取上限要略高于最终入库页数。
        fetch_limit = max(max_pages * 8, max_pages + 10)

        while queue and len(plan.pages) < max_pages and len(visited) < fetch_limit:
            current_url, depth = queue.popleft()
            if current_url in visited:
                continue

            visited.add(current_url)
            html = self.browser.fetch_page(current_url)
            if not html:
                continue

            title = self.browser.extract_title(html) or current_url
            if not plan.title:
                plan.title = title

            text = self.browser.extract_text(html)
            if self._is_usable_content_page(current_url, title, text, min_content_chars):
                plan.pages.append({
                    "url": current_url,
                    "title": title,
                    "order": len(plan.pages),
                    "depth": depth,
                    "root_url": root_url,
                    "content_chars": len(text.strip()),
                })

            if depth >= max_depth:
                continue

            links = self.browser.extract_links(html, current_url)
            candidates = []
            for link in links:
                normalized = self._normalize_url(link)
                if normalized in visited or normalized in queued:
                    continue
                if self._is_crawlable_subpage(normalized, root_url):
                    candidates.append(normalized)

            for link in sorted(set(candidates), key=lambda item: self._link_sort_key(item, topic_terms)):
                queued.add(link)
                queue.append((link, depth + 1))

        if not plan.title:
            plan.title = url

        logger.info(
            f"网页学习计划: {plan.title} | 可用页面={len(plan.pages)} "
            f"| 已探测={len(visited)} | depth={max_depth}"
        )
        return plan

    @staticmethod
    def _normalize_url(url: str) -> str:
        """去掉锚点/查询参数，用于同页去重。"""
        parts = urlsplit(url.strip())
        path = parts.path or "/"
        if path != "/":
            path = path.rstrip("/")
        return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, "", ""))

    @staticmethod
    def _topic_terms(topic: str) -> List[str]:
        return [
            term.lower()
            for term in re.split(r"[\s,，;；/|]+", topic or "")
            if len(term.strip()) >= 2
        ]

    def _is_crawlable_subpage(self, link: str, root_url: str) -> bool:
        parsed_link = urlparse(link)
        parsed_root = urlparse(root_url)
        if parsed_link.scheme not in ("http", "https"):
            return False
        if parsed_link.netloc != parsed_root.netloc:
            return False

        path = unquote(parsed_link.path or "/").lower()
        if path.endswith(self.ASSET_EXTENSIONS):
            return False
        if any(part in path for part in self.LOW_VALUE_PATH_PARTS):
            return False

        scope_path = self._crawl_scope_path(root_url)
        if scope_path and not (path == scope_path or path.startswith(scope_path + "/")):
            return False
        return True

    def _crawl_scope_path(self, root_url: str) -> str:
        """
        从入口 URL 推断安全爬取范围，避免同域名下跨产品线乱跳。

        例如 HuggingFace 的 /docs/transformers/index 只应继续读取
        /docs/transformers/*，不应混入 /learn/llm-course/*。
        """
        parsed = urlparse(root_url)
        path = unquote(parsed.path or "/").strip("/").lower()
        if not path:
            return ""

        parts = [part for part in path.split("/") if part]
        if not parts:
            return ""
        if parts[-1] in ("index", "home", "overview", "introduction"):
            parts = parts[:-1]
        elif "." in parts[-1]:
            parts = parts[:-1]

        if not parts:
            return ""

        doc_roots = {"docs", "documentation", "learn", "course", "courses", "tutorial"}
        if parts[0] in doc_roots and len(parts) >= 2:
            return "/" + "/".join(parts[:2])
        return "/" + parts[0]

    def _is_usable_content_page(
        self,
        url: str,
        title: str,
        text: str,
        min_content_chars: int,
    ) -> bool:
        path = unquote(urlparse(url).path or "/").lower()
        if path.endswith(self.ASSET_EXTENSIONS):
            return False
        if any(part in path for part in self.LOW_VALUE_PATH_PARTS):
            return False

        compact = re.sub(r"\s+", " ", text or "").strip()
        if len(compact) < min_content_chars:
            return False

        login_signals = (
            "登录", "登陆", "注册", "验证码", "sign in", "log in",
            "sign up", "password", "forgot password", "captcha",
        )
        haystack = f"{title} {compact[:1000]}".lower()
        signal_count = sum(1 for signal in login_signals if signal in haystack)
        if signal_count >= 2 and len(compact) < 1500:
            return False

        return True

    def _link_sort_key(self, link: str, topic_terms: List[str]):
        path = unquote(urlparse(link).path or "/").lower()
        score = 0
        for hint in self.CONTENT_PATH_HINTS:
            if hint in path:
                score += 10
        for term in topic_terms:
            if term and term in path:
                score += 5
        depth = len([part for part in path.split("/") if part])
        return (-score, depth, path)

    def _find_github_urls(self, html: str) -> List[str]:
        """从HTML中提取GitHub仓库URL"""
        pattern = r'https?://github\.com/[\w\-\.]+/[\w\-\.]+'
        urls = set(re.findall(pattern, html))
        # 过滤掉非仓库链接
        result = []
        for url in urls:
            parts = urlparse(url).path.strip("/").split("/")
            if len(parts) == 2:  # owner/repo 格式
                result.append(url)
        return result

    def _find_arxiv_urls(self, html: str) -> List[str]:
        """从HTML中提取ArXiv论文URL"""
        pattern = r'https?://arxiv\.org/(?:abs|pdf)/\d{4}\.\d{4,5}'
        return list(set(re.findall(pattern, html)))
