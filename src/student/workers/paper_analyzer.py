"""
ArXiv论文分析Worker (PaperAnalyzer)
=====================================
下载ArXiv论文PDF并进行结构化分析。
"""

import re
from src.core.worker import BaseWorker, WorkerSpec, WorkerInput, WorkerOutput
from src.core.material_store import Material
from src.researchers.arxiv_researcher import ArxivResearcher
from src.utils.logger import logger


class PaperAnalyzer(BaseWorker):
    """ArXiv论文结构化分析Worker"""

    def __init__(self):
        super().__init__(WorkerSpec(
            name="PaperAnalyzer",
            description="下载并结构化分析ArXiv论文",
            model_level="deep",
            max_retries=2,
            timeout=180,
        ))
        self.arxiv = ArxivResearcher()

    def execute(self, input_data: WorkerInput) -> WorkerOutput:
        url = input_data.url
        if not url:
            return WorkerOutput(success=False, error="缺少ArXiv URL")

        # 提取ArXiv ID
        arxiv_id = self._extract_arxiv_id(url)
        if not arxiv_id:
            return WorkerOutput(success=False, error=f"无法提取ArXiv ID: {url}")

        # 搜索论文信息
        papers = self.arxiv.search_papers(arxiv_id, max_results=1)
        if not papers:
            return WorkerOutput(success=False, error=f"未找到论文: {arxiv_id}")

        paper = papers[0]

        # 下载并解析PDF
        pdf_text = self.arxiv.download_and_parse(paper['pdf_url'], paper['title'])
        if not pdf_text:
            pdf_text = paper.get('summary', '')

        # LLM结构化分析
        analysis = self._analyze_paper(paper, pdf_text)

        # 构建完整内容
        full_content = self._build_full_content(paper, pdf_text, analysis)

        material = Material(
            source_url=url,
            source_type="arxiv",
            title=paper['title'],
            content=full_content,
            summary=analysis.get("summary", paper.get("summary", "")),
            tags=paper.get("categories", []),
            metadata={
                "arxiv_id": arxiv_id,
                "authors": paper.get("authors", []),
                "published": paper.get("published", ""),
                "pdf_url": paper.get("pdf_url", ""),
            }
        )

        return WorkerOutput(
            success=True,
            content=full_content,
            data={"paper": paper, "analysis": analysis},
            materials=[material],
        )

    def _extract_arxiv_id(self, url: str) -> str:
        match = re.search(r'(\d{4}\.\d{4,5})', url)
        return match.group(1) if match else ""

    def _analyze_paper(self, paper: dict, pdf_text: str) -> dict:
        """用LLM结构化分析论文"""
        # 取PDF前部分（通常包含摘要和引言）
        text_sample = pdf_text[:8000] if pdf_text else paper.get("summary", "")

        prompt = f"""请对以下ArXiv论文进行结构化分析。

标题: {paper['title']}
作者: {', '.join(paper.get('authors', [])[:5])}
摘要: {paper.get('summary', '')}

论文正文（节选）:
{text_sample}

请用中文提供：
1. 一句话总结（不超过100字）
2. 研究问题与动机
3. 方法/模型概述
4. 关键创新点
5. 实验结果要点
6. 局限性与未来方向"""

        try:
            result = self.llm_call(
                prompt,
                system="你是AI领域论文分析专家。请提供深入的技术分析，保持学术严谨性。",
                enable_thinking=True,
            )
            return {"summary": result[:200], "analysis": result}
        except Exception as e:
            logger.warning(f"论文分析失败: {e}")
            return {"summary": paper.get("summary", "")[:200], "analysis": ""}

    def _build_full_content(self, paper: dict, pdf_text: str, analysis: dict) -> str:
        """构建完整的论文内容文本"""
        parts = []
        parts.append(f"# {paper['title']}")
        parts.append(f"\n**作者**: {', '.join(paper.get('authors', []))}")
        parts.append(f"**发布日期**: {paper.get('published', '')}")
        parts.append(f"**ArXiv**: {paper.get('entry_id', '')}")

        if analysis.get("analysis"):
            parts.append(f"\n## 结构化分析\n{analysis['analysis']}")

        parts.append(f"\n## 原文摘要\n{paper.get('summary', '')}")

        if pdf_text:
            parts.append(f"\n## 论文全文\n{pdf_text}")

        return "\n".join(parts)
