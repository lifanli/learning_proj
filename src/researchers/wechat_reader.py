from src.agents.base_agent import BaseAgent
from src.tools.web_browser import WebBrowser
from src.tools.github_api import GitHubAPI
from src.tools.web_search import WebSearch
from src.utils.logger import logger
import re
from bs4 import BeautifulSoup, NavigableString, Tag


class WechatReader(BaseAgent):
    def __init__(self):
        super().__init__(
            role_name="微信阅读员",
            role_instruction="你是一名专业的微信公众号文章阅读员。你的任务是从微信文章中提取关键技术信息，识别引用的技术项目，并解读图片内容。输出必须为中文。"
        )
        self.browser = WebBrowser()
        self.github = GitHubAPI()
        self.search = WebSearch()

    def process_article(self, url: str) -> dict:
        """
        处理微信文章：提取文本（图片就地内嵌）、查找 GitHub 链接、获取仓库信息、解读图片。
        """
        logger.info(f"正在处理微信文章: {url}")

        # 1. 抓取文章
        html = self.browser.fetch_page(url)
        if not html:
            return {"error": "页面抓取失败"}

        # 提取标题
        title = self.browser.extract_title(html) or ""
        if title:
            title = title.split("-")[0].split("|")[0].strip()

        # 提取内容（图片已内嵌为 markdown 语法）和图片列表
        content, images = self._clean_wechat_article_with_images(html)

        # 2. 多模态图片解读（只对内容图片做）
        image_interpretations = []
        for img_url in images[:3]:
            interpretation = self._interpret_image(img_url)
            if interpretation:
                image_interpretations.append({
                    "url": img_url,
                    "description": interpretation
                })

        # 3. 提取 GitHub 链接
        github_links = self._find_github_links(content)

        # 4. 处理 GitHub 链接（验证/搜索/获取）
        repos_info = []
        for link in github_links:
            repo_data = self.github.get_repo_content(link)
            if not repo_data:
                logger.info(f"链接 {link} 可能已失效，正在搜索替代...")
                project_name = link.split("/")[-1]
                new_link = self.search.search_first_link(f"GitHub {project_name}")
                if new_link and "github.com" in new_link:
                    logger.info(f"找到替代链接: {new_link}")
                    repo_data = self.github.get_repo_content(new_link)

            if repo_data:
                repos_info.append(repo_data)

        return {
            "source_url": url,
            "title": title or "微信文章",
            "content": content,
            "image_interpretations": image_interpretations,
            "related_repos": repos_info
        }

    def _clean_wechat_article_with_images(self, html: str) -> tuple[str, list]:
        """
        从微信文章中顺序提取文本和图片，图片就地替换为 markdown 图片语法。
        返回 (content_with_images, content_images)
        """
        soup = BeautifulSoup(html, "html.parser")
        content_div = soup.find(id="js_content")

        if not content_div:
            return self.browser.extract_text(html), []

        # 移除脚本/样式
        for tag in content_div(["script", "style"]):
            tag.extract()

        # 计算总元素数用于位置百分比判断
        all_elements = list(content_div.descendants)
        total_elements = len(all_elements)

        content_images = []
        parts = []

        def _get_element_position(element):
            """获取元素在内容中的大致位置百分比"""
            try:
                idx = all_elements.index(element)
                return idx / total_elements if total_elements > 0 else 0
            except ValueError:
                return 0

        def _process_element(element):
            """递归处理元素，顺序提取文本和图片"""
            if isinstance(element, NavigableString):
                text = str(element).strip()
                if text:
                    parts.append(text)
                return

            if not isinstance(element, Tag):
                return

            # 处理 img 标签
            if element.name == 'img':
                src = element.get('data-src') or element.get('src')
                if src and src.startswith('http'):
                    position = _get_element_position(element)
                    if not self._is_ad_image(element, position):
                        parts.append(f"\n\n![]({src})\n\n")
                        content_images.append(src)
                return

            # 处理块级元素：在前后添加换行
            block_tags = {'p', 'div', 'section', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                          'blockquote', 'pre', 'ul', 'ol', 'li', 'br', 'hr'}
            is_block = element.name in block_tags

            if is_block:
                parts.append('\n')

            for child in element.children:
                _process_element(child)

            if is_block:
                parts.append('\n')

        _process_element(content_div)

        # 合并文本，清理多余空行
        raw_text = ''.join(parts)
        # 将连续多个换行压缩为两个
        text = re.sub(r'\n{3,}', '\n\n', raw_text).strip()

        return text, content_images

    def _is_ad_image(self, img_tag: Tag, position: float) -> bool:
        """
        判断图片是否为广告/装饰图。
        Args:
            img_tag: BeautifulSoup img 标签
            position: 图片在文章中的位置百分比 (0.0 ~ 1.0)
        Returns:
            True 表示是广告图，应过滤
        """
        src = img_tag.get('data-src') or img_tag.get('src') or ''

        # 规则 1: URL 包含二维码/打赏关键词
        ad_keywords = ['qrcode', 'reward', 'qr_code', 'donate', 'red_packet']
        if any(kw in src.lower() for kw in ad_keywords):
            logger.debug(f"过滤广告图片(URL关键词): {src[:80]}")
            return True

        # 规则 2: data-type="gif" 且尺寸小 → 装饰性 GIF
        if img_tag.get('data-type') == 'gif':
            width = img_tag.get('data-w') or img_tag.get('width') or '0'
            try:
                w = int(str(width).replace('px', ''))
                if w < 100:
                    logger.debug(f"过滤装饰GIF(尺寸小): {src[:80]}")
                    return True
            except (ValueError, TypeError):
                pass

        # 规则 3: 图片宽度 < 50px → 图标
        width = img_tag.get('data-w') or img_tag.get('width') or '0'
        try:
            w = int(str(width).replace('px', ''))
            if 0 < w < 50:
                logger.debug(f"过滤图标(宽度<50): {src[:80]}")
                return True
        except (ValueError, TypeError):
            pass

        # 规则 4: 位于文章最后 20% 的二维码类图片
        if position > 0.8:
            # 检查 class 或周围文字是否含二维码相关信息
            img_class = ' '.join(img_tag.get('class', []))
            parent = img_tag.parent
            parent_text = parent.get_text() if parent else ''
            qr_hints = ['二维码', 'qrcode', '扫码', '关注', '公众号', '长按识别']
            if any(hint in (img_class + parent_text).lower() for hint in qr_hints):
                logger.debug(f"过滤公众号推广(尾部二维码): {src[:80]}")
                return True

        # 规则 5: mmbiz_gif 且非内容核心区域（前 20% 或后 20%）
        if 'mmbiz_gif' in src:
            if position < 0.2 or position > 0.8:
                logger.debug(f"过滤装饰动图(mmbiz_gif边缘): {src[:80]}")
                return True

        return False

    def _interpret_image(self, img_url: str) -> str:
        """
        使用视觉多模态模型解读图片。
        """
        logger.info(f"正在解读图片: {img_url}")
        try:
            vision_model = self.config.get("models", {}).get("vision", "qwen3.6-plus")
            return self.llm_client.chat_completion_with_images(
                prompt="请用中文详细描述这张技术图表或图片。重点关注架构组件、数据流或关键洞察。",
                image_urls=[img_url],
                model=vision_model,
            )
        except Exception as e:
            logger.warning(f"图片解读失败 {img_url}: {e}")
            return ""

    def _find_github_links(self, text: str) -> list:
        """查找文本中的 GitHub 链接"""
        pattern = r"https?://github\.com/[a-zA-Z0-9-]+/[a-zA-Z0-9-_.]+"
        links = re.findall(pattern, text)
        return list(set(links))


if __name__ == "__main__":
    reader = WechatReader()
    print("微信阅读员已初始化。")
