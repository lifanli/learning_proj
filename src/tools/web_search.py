import random
import time

try:
    from ddgs import DDGS
except ImportError:  # 兼容旧依赖 duckduckgo-search
    from duckduckgo_search import DDGS
from src.utils.logger import logger
from typing import List, Dict, Optional


class WebSearch:
    """封装 DuckDuckGo 搜索为可复用工具，带指数退避重试"""

    def __init__(self, max_results: int = 5, max_retries: int = 3):
        self.max_results = max_results
        self.max_retries = max_retries
        self._last_call_time = 0.0

    def _wait_between_calls(self):
        """请求间随机延迟 3-8 秒，避免触发限流"""
        elapsed = time.time() - self._last_call_time
        min_interval = 3.0 + random.random() * 5.0  # 3-8 秒
        if elapsed < min_interval:
            sleep_time = min_interval - elapsed
            logger.debug(f"搜索限流保护: 等待 {sleep_time:.1f}s")
            time.sleep(sleep_time)
        self._last_call_time = time.time()

    def search(self, query: str, max_results: Optional[int] = None) -> List[Dict]:
        """
        执行 DuckDuckGo 搜索，返回结果列表。
        每个结果包含 title, href, body 字段。
        带指数退避重试（3 次），遇到限流自动等待后重试。
        """
        num = max_results or self.max_results
        logger.info(f"正在搜索: {query} (最多 {num} 条结果)")

        for attempt in range(self.max_retries):
            self._wait_between_calls()
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=num))
                logger.info(f"搜索完成，获得 {len(results)} 条结果")
                return results
            except Exception as e:
                error_str = str(e)
                is_ratelimit = "429" in error_str or "ratelimit" in error_str.lower() or "rate limit" in error_str.lower()
                if is_ratelimit and attempt < self.max_retries - 1:
                    backoff = (2 ** attempt) * 5 + random.random() * 5  # 5-15s, 10-25s, ...
                    logger.warning(
                        f"搜索限流，第 {attempt + 1} 次重试，等待 {backoff:.1f}s: {query}"
                    )
                    time.sleep(backoff)
                else:
                    logger.error(f"搜索失败: {e}")
                    return []

        return []

    def search_first_link(self, query: str) -> Optional[str]:
        """搜索并返回第一个结果的链接"""
        results = self.search(query, max_results=1)
        if results:
            return results[0].get("href")
        return None
