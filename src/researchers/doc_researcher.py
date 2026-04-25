import hashlib
import json
import os
import re
import time
from collections import deque
from src.agents.base_agent import BaseAgent
from src.tools.web_browser import WebBrowser
from src.utils.logger import logger
from urllib.parse import urljoin, urlparse


class DocResearcher(BaseAgent):
    HASH_FILE = "data/doc_hashes.json"

    def __init__(self):
        super().__init__(
            role_name="文档研究员",
            role_instruction="你是一名细致的技术文档研究员。你的目标是深入理解文档的结构和内容，提取关键技术信息。输出必须为中文。"
        )
        self.browser = WebBrowser()
        self.visited_urls = set()
        self.hashes = self._load_hashes()

    def _load_hashes(self) -> dict:
        """加载已记录的内容哈希"""
        try:
            if os.path.exists(self.HASH_FILE):
                with open(self.HASH_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"加载哈希文件失败: {e}")
        return {}

    def _save_hashes(self):
        """保存内容哈希到文件"""
        os.makedirs(os.path.dirname(self.HASH_FILE), exist_ok=True)
        with open(self.HASH_FILE, "w", encoding="utf-8") as f:
            json.dump(self.hashes, f, ensure_ascii=False, indent=2)

    def _content_hash(self, text: str) -> str:
        """计算内容的 SHA256 哈希"""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _is_content_changed(self, url: str, content: str) -> bool:
        """检查页面内容是否有变化"""
        new_hash = self._content_hash(content)
        old_hash = self.hashes.get(url)

        if old_hash == new_hash:
            logger.info(f"页面内容未变化，跳过: {url}")
            return False

        # 更新哈希
        self.hashes[url] = new_hash
        return True

    def research_doc(self, start_url: str, max_depth: int = 1, max_pages: int = 5) -> dict:
        """
        递归阅读文档，支持增量学习（跳过未变化的页面）。
        """
        logger.info(f"开始研究文档: {start_url}")
        self.visited_urls.clear()

        pages_content = []
        skipped_count = 0
        queue = [(start_url, 0)]

        domain = urlparse(start_url).netloc
        base_path = urlparse(start_url).path

        while queue and len(pages_content) < max_pages:
            current_url, depth = queue.pop(0)

            if current_url in self.visited_urls:
                continue

            if depth > max_depth:
                continue

            logger.info(f"正在阅读页面: {current_url}")
            html = self.browser.fetch_page(current_url)
            if not html:
                continue

            self.visited_urls.add(current_url)
            text = self.browser.extract_text(html)

            # 增量学习：检查内容是否变化
            if not self._is_content_changed(current_url, text):
                skipped_count += 1
                continue

            pages_content.append({
                "url": current_url,
                "title": self.browser.extract_title(html) or current_url,
                "content": text[:5000]
            })

            # 查找子链接（extract_links 已返回绝对 URL）
            links = self.browser.extract_links(html, current_url)
            for link in links:
                parsed_link = urlparse(link)

                if parsed_link.netloc == domain and parsed_link.path.startswith(base_path):
                    if link not in self.visited_urls:
                        queue.append((link, depth + 1))

            time.sleep(1)  # 礼貌延迟

        # 保存更新后的哈希
        self._save_hashes()

        if skipped_count > 0:
            logger.info(f"增量学习：跳过了 {skipped_count} 个未变化的页面")

        logger.info(f"文档研究完成，获取了 {len(pages_content)} 个新/更新页面")

        return {
            "root_url": start_url,
            "pages": pages_content,
            "skipped": skipped_count
        }

    def _discover_course_root(self, start_url: str) -> tuple[str, list]:
        """
        从给定 URL 向上回溯路径，找到能发现最多课程链接的根 URL。
        例如: /learn/llm-course/chapter0/1 → /learn/llm-course/chapter0 → /learn/llm-course
        始终尝试所有层级，选链接最多的那层作为课程根。
        返回 (course_root_url, filtered_links)
        """
        parsed = urlparse(start_url)
        # 候选路径：从当前路径逐级向上
        path = parsed.path.rstrip('/')
        candidates = []
        while path and path != '/':
            candidates.append(path)
            path = '/'.join(path.split('/')[:-1])

        best_url = start_url
        best_links = []

        for candidate_path in candidates:
            candidate_url = f"{parsed.scheme}://{parsed.netloc}{candidate_path}"
            logger.info(f"[课程根探测] 尝试: {candidate_url}")

            html = self.browser.fetch_page(candidate_url)
            if not html:
                continue

            links = self.browser.discover_course_links(html, candidate_url)

            # 过滤：只保留以 candidate_path 为前缀的链接，排除多语言版本
            base_segments = candidate_path.strip('/').split('/')
            expected_depth = len(base_segments)

            def _is_main_content(url):
                p = urlparse(url).path.strip('/')
                parts = p.split('/')
                if len(parts) <= expected_depth:
                    return False
                # 紧跟 base 的第一段不能是语言代码（en, zh-CN, pt-BR, rum 等）
                next_seg = parts[expected_depth]
                if re.match(r'^[a-zA-Z]{2,3}(-[a-zA-Z]{2,3})?$', next_seg):
                    return False
                # 排除 events 等非课程内容
                if next_seg in ('events', 'assets', 'static'):
                    return False
                return True

            filtered = [l for l in links if _is_main_content(l)]
            logger.info(f"[课程根探测] {candidate_url} → {len(filtered)} 个课程链接")

            if len(filtered) > len(best_links):
                best_links = filtered
                best_url = candidate_url

            # 如果当前层级链接数比上一层更少，说明已经过了最优层，提前终止
            elif len(filtered) < len(best_links) and len(best_links) > 0:
                logger.info(f"[课程根探测] 链接数开始减少，停止回溯")
                break

        logger.info(f"[课程根探测] 确定课程根: {best_url} ({len(best_links)} 个链接)")
        return best_url, best_links

    def research_course(self, start_url: str, max_depth: int = 3, max_pages: int = 50) -> dict:
        """
        课程感知爬虫：
        第一步：自动回溯找到课程根 URL，用 discover_course_links 深度提取全部章节链接
        第二步：按自然排序顺序逐页爬取
        """
        logger.info(f"开始研究课程: {start_url} (max_depth={max_depth}, max_pages={max_pages})")
        self.visited_urls.clear()

        pages_content = []
        page_order = []
        skipped_count = 0
        order_index = 0

        # === 第一步：自动回溯找到课程根，深度发现链接 ===
        course_root, all_course_links = self._discover_course_root(start_url)
        logger.info(f"[课程爬取] 课程根: {course_root}, 发现 {len(all_course_links)} 个链接")

        if not all_course_links:
            logger.warning("[课程爬取] 未发现课程链接，仅处理起始页")
            all_course_links = [start_url]

        # === 第二步：按顺序爬取每个链接 ===
        for course_url in all_course_links:
            if len(pages_content) >= max_pages:
                logger.info(f"[课程爬取] 已达最大页面数 {max_pages}，停止")
                break

            if course_url in self.visited_urls:
                continue

            logger.info(f"[课程爬取] 页面 {order_index + 1}/{len(all_course_links)}: {course_url}")
            page_html = self.browser.fetch_page(course_url)
            if not page_html:
                continue

            self.visited_urls.add(course_url)
            text = self.browser.extract_text(page_html)

            # 增量学习：检查内容是否变化
            if not self._is_content_changed(course_url, text):
                skipped_count += 1
                time.sleep(0.5)
                continue

            title = self.browser.extract_title(page_html) or course_url

            pages_content.append({
                "url": course_url,
                "title": title,
                "content": text[:8000],
                "order": order_index,
                "depth": 0
            })
            page_order.append({
                "order": order_index,
                "url": course_url,
                "title": title
            })
            order_index += 1
            time.sleep(1)  # 礼貌延迟

        # 保存更新后的哈希
        self._save_hashes()

        if skipped_count > 0:
            logger.info(f"增量学习：跳过了 {skipped_count} 个未变化的页面")

        logger.info(f"课程研究完成，获取了 {len(pages_content)} 个页面，共 {order_index} 章节")

        return {
            "root_url": course_root,
            "pages": pages_content,
            "page_order": page_order,
            "skipped": skipped_count
        }
