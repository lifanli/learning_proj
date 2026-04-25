"""
学习计划管理器 (StudyPlanner)
=============================
分析输入URL/主题，制定学习计划，确定需要抓取的所有页面和任务。
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from urllib.parse import urlparse

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
