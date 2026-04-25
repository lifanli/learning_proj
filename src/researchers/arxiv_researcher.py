import arxiv
import datetime
import os
from typing import List, Dict
from src.utils.logger import logger
from src.tools.pdf_parser import PDFParser
import requests


class ArxivResearcher:
    def __init__(self, download_dir: str = "data/arxiv_pdfs"):
        self.client = arxiv.Client()
        self.download_dir = download_dir
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)

    def search_papers(self, query: str, max_results: int = 5) -> List[Dict]:
        """搜索 ArXiv 论文"""
        logger.info(f"正在搜索 ArXiv: {query}")
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )

        results = []
        for result in self.client.results(search):
            paper_info = {
                "title": result.title,
                "authors": [a.name for a in result.authors],
                "summary": result.summary,
                "published": result.published.strftime("%Y-%m-%d"),
                "pdf_url": result.pdf_url,
                "entry_id": result.entry_id,
                "categories": result.categories
            }
            results.append(paper_info)

        logger.info(f"找到 {len(results)} 篇论文")
        return results

    def fetch_daily_updates(self, categories: List[str] = ["cs.AI", "cs.LG", "cs.CL"], max_results: int = 10) -> List[Dict]:
        """获取指定分类的最新论文"""
        query = " OR ".join([f"cat:{cat}" for cat in categories])
        return self.search_papers(query, max_results=max_results)

    def download_and_parse(self, paper_url: str, title: str) -> str:
        """下载 PDF 并提取文本"""
        try:
            safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '-', '_')]).strip()
            safe_title = safe_title[:50]
            file_path = os.path.join(self.download_dir, f"{safe_title}.pdf")

            if not os.path.exists(file_path):
                logger.info(f"正在下载 PDF: {title}")
                response = requests.get(paper_url)
                if response.status_code == 200:
                    with open(file_path, "wb") as f:
                        f.write(response.content)
                else:
                    logger.error(f"PDF 下载失败，状态码: {response.status_code}")
                    return ""

            logger.info(f"正在解析 PDF: {file_path}")
            text = PDFParser.extract_text_from_pdf(file_path)
            return text

        except Exception as e:
            logger.error(f"处理论文 {title} 时出错: {e}")
            return ""


if __name__ == "__main__":
    researcher = ArxivResearcher()
    papers = researcher.search_papers("DeepSeek", max_results=1)
    if papers:
        print(f"标题: {papers[0]['title']}")
        content = researcher.download_and_parse(papers[0]['pdf_url'], papers[0]['title'])
        print(f"内容长度: {len(content)}")
