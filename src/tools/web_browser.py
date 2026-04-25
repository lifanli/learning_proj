import requests
import os
import hashlib
from bs4 import BeautifulSoup, NavigableString, Tag
from src.utils.logger import logger
from urllib.parse import urljoin, urlparse
import re

class WebBrowser:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    def fetch_page(self, url: str) -> str:
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return ""

    def extract_text(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")

        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.extract()

        text = soup.get_text()

        # Break into lines and remove leading/trailing space on each
        lines = (line.strip() for line in text.splitlines())
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # Drop blank lines
        text = '\n'.join(chunk for chunk in chunks if chunk)

        return text

    def extract_content_with_images(self, html: str, base_url: str = "") -> dict:
        """
        提取页面内容，保留图片位置信息，不截断。
        返回:
        {
            "text": "完整文本（图片位置用占位符）",
            "images": [{"url": "...", "alt": "...", "position": 123}],
            "code_blocks": [{"language": "python", "code": "..."}],
            "headings": [{"level": 1, "text": "..."}],
        }
        """
        soup = BeautifulSoup(html, "html.parser")

        # Remove unwanted elements
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.extract()

        # Find main content area
        content_area = (
            soup.find("article") or
            soup.find("main") or
            soup.find(id="js_content") or  # WeChat
            soup.find(class_=re.compile(r"(content|article|post|entry)", re.I)) or
            soup.body or
            soup
        )

        images = []
        code_blocks = []
        headings = []
        text_parts = []
        img_counter = 0

        for element in content_area.descendants:
            if isinstance(element, NavigableString):
                stripped = element.strip()
                if stripped:
                    text_parts.append(stripped)

            elif isinstance(element, Tag):
                # 提取图片
                if element.name == "img":
                    src = element.get("src", "") or element.get("data-src", "")
                    if src:
                        if base_url and not src.startswith("http"):
                            src = urljoin(base_url, src)
                        alt = element.get("alt", "")
                        img_placeholder = f"[IMAGE_{img_counter}: {alt or 'image'}]"
                        text_parts.append(img_placeholder)
                        images.append({
                            "url": src,
                            "alt": alt,
                            "position": len("\n".join(text_parts)),
                            "index": img_counter,
                        })
                        img_counter += 1

                # 提取代码块
                elif element.name == "pre":
                    code_tag = element.find("code")
                    if code_tag:
                        code_text = code_tag.get_text()
                        # 检测语言
                        lang = ""
                        classes = code_tag.get("class", [])
                        for cls in classes:
                            if cls.startswith("language-") or cls.startswith("lang-"):
                                lang = cls.split("-", 1)[1]
                                break
                        code_blocks.append({"language": lang, "code": code_text})
                        text_parts.append(f"\n```{lang}\n{code_text}\n```\n")

                # 提取标题
                elif element.name in ("h1", "h2", "h3", "h4", "h5", "h6"):
                    level = int(element.name[1])
                    heading_text = element.get_text(strip=True)
                    if heading_text:
                        headings.append({"level": level, "text": heading_text})

        full_text = "\n".join(text_parts)

        return {
            "text": full_text,
            "images": images,
            "code_blocks": code_blocks,
            "headings": headings,
        }

    def download_image(self, image_url: str, save_dir: str, timeout: int = 15) -> str:
        """
        下载图片到指定目录，返回本地文件路径。
        文件名基于URL的hash，避免重复下载。
        """
        try:
            os.makedirs(save_dir, exist_ok=True)

            # 生成稳定的文件名
            url_hash = hashlib.md5(image_url.encode()).hexdigest()[:12]
            # 从URL提取扩展名
            parsed = urlparse(image_url)
            path_ext = os.path.splitext(parsed.path)[1]
            ext = path_ext if path_ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg") else ".jpg"
            filename = f"{url_hash}{ext}"
            local_path = os.path.join(save_dir, filename)

            # 已存在则跳过
            if os.path.exists(local_path):
                return local_path

            response = requests.get(image_url, headers=self.headers, timeout=timeout, stream=True)
            response.raise_for_status()

            # 检查是否真的是图片
            content_type = response.headers.get("Content-Type", "")
            if content_type and "image" not in content_type and "octet-stream" not in content_type:
                logger.warning(f"非图片内容类型: {content_type} for {image_url}")
                return ""

            with open(local_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.debug(f"图片已下载: {image_url} -> {local_path}")
            return local_path

        except Exception as e:
            logger.warning(f"图片下载失败 {image_url}: {e}")
            return ""

    def extract_links(self, html: str, base_url: str) -> list:
        soup = BeautifulSoup(html, "html.parser")
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href'].strip()

            # 过滤锚点、javascript、mailto 链接
            if not href or href.startswith('#') or href.startswith('javascript:') or href.startswith('mailto:'):
                continue

            # 使用 urljoin 将相对路径转为绝对路径
            full_url = urljoin(base_url, href)

            # 只保留 http/https 链接
            if full_url.startswith('http://') or full_url.startswith('https://'):
                # 去掉 URL 中的锚点部分
                full_url = full_url.split('#')[0]
                if full_url:
                    links.append(full_url)

        return list(set(links))

    def extract_title(self, html: str) -> str:
        try:
            soup = BeautifulSoup(html, "html.parser")
            return soup.title.string if soup.title else ""
        except:
            return ""

    def clean_wechat_article(self, html: str) -> str:
        """
        Specific cleaner for WeChat articles to remove QR codes, ads, etc.
        """
        soup = BeautifulSoup(html, "html.parser")

        # WeChat content is usually in #js_content
        content_div = soup.find(id="js_content")
        if content_div:
            # Remove scripts/styles
            for tag in content_div(["script", "style"]):
                tag.extract()
            text = content_div.get_text(separator="\n")
        else:
            # Fallback
            text = self.extract_text(html)

        return text.strip()

    def discover_course_links(self, html: str, base_url: str) -> list:
        """
        深度链接发现：除了 <a href> 之外，还从整个 HTML 源码中
        用正则提取相对路径（如 chapter1/2），拼成完整 URL。
        专门用于 JS 渲染的课程站点（链接藏在 data-props / JSON 中）。
        返回按自然排序的去重链接列表。
        """
        parsed_base = urlparse(base_url)
        base_path = parsed_base.path.rstrip('/')  # e.g. /learn/llm-course

        # 1. 先收集 <a href> 中的常规链接
        links = set(self.extract_links(html, base_url))

        # 2. 从整个 HTML 源码中正则提取相对路径片段
        #    匹配如 "chapter1/2" 或 "/learn/llm-course/chapter1/2" 形式
        #    绝对路径形式
        abs_pattern = re.escape(base_path) + r'/[\w\-/]+'
        for match in re.findall(abs_pattern, html):
            full_url = f"{parsed_base.scheme}://{parsed_base.netloc}{match}"
            full_url = full_url.split('#')[0].split('?')[0]
            links.add(full_url)

        #    相对路径片段（从 data-props、JSON、JS 中提取）
        #    提取被引号包裹的相对路径，如 "chapter1/2" 或 "/chapter1/2"
        rel_pattern = r'["\'/](' + re.escape(base_path.split('/')[-1]) + r'/[\w\-]+(?:/[\w\-]+)*)["\']'
        for match in re.findall(rel_pattern, html):
            # match 可能是 "llm-course/chapter1/2"
            # 需要拼成完整路径
            if match.startswith('/'):
                full_url = f"{parsed_base.scheme}://{parsed_base.netloc}{match}"
            else:
                # 拼到 base_path 的父目录下
                parent_path = '/'.join(base_path.split('/')[:-1])
                full_url = f"{parsed_base.scheme}://{parsed_base.netloc}{parent_path}/{match}"
            full_url = full_url.split('#')[0].split('?')[0]
            links.add(full_url)

        # 3. 过滤：只保留 base_path 前缀下的链接
        filtered = []
        for link in links:
            p = urlparse(link)
            if p.netloc == parsed_base.netloc and p.path.startswith(base_path + '/'):
                filtered.append(link)

        # 4. 自然排序（chapter2 排在 chapter10 前面）
        def sort_key(url):
            parts = urlparse(url).path.split('/')
            result = []
            for part in parts:
                # 拆分数字和非数字部分，实现自然排序
                for sub in re.split(r'(\d+)', part):
                    result.append(int(sub) if sub.isdigit() else sub)
            return result

        filtered.sort(key=sort_key)

        logger.info(f"深度链接发现: 从 {base_url} 提取到 {len(filtered)} 个课程链接")
        return filtered
