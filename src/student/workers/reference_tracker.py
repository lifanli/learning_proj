"""
引用追踪Worker (ReferenceTracker)
===================================
从页面内容中发现GitHub/ArXiv/外部文档链接，生成新的学习任务。
"""

import re
from urllib.parse import urlparse
from src.core.worker import BaseWorker, WorkerSpec, WorkerInput, WorkerOutput
from src.utils.logger import logger


class ReferenceTracker(BaseWorker):
    """引用追踪Worker"""

    def __init__(self):
        super().__init__(WorkerSpec(
            name="ReferenceTracker",
            description="追踪内容中的GitHub/ArXiv/文档引用链接",
            model_level="fast",  # 不需要LLM，纯正则
            max_retries=1,
        ))

    def execute(self, input_data: WorkerInput) -> WorkerOutput:
        content = input_data.content
        html = input_data.extra.get("html", "")
        text = content + "\n" + html  # 同时搜索纯文本和HTML

        references = []

        # GitHub仓库链接
        github_pattern = r'https?://github\.com/([\w\-\.]+)/([\w\-\.]+)(?:/(?:tree|blob)/[\w\-\.]+)?'
        for match in re.finditer(github_pattern, text):
            url = f"https://github.com/{match.group(1)}/{match.group(2)}"
            references.append({
                "url": url,
                "type": "github",
                "title": f"{match.group(1)}/{match.group(2)}",
            })

        # ArXiv论文链接
        arxiv_pattern = r'https?://arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})'
        for match in re.finditer(arxiv_pattern, text):
            arxiv_id = match.group(1)
            url = f"https://arxiv.org/abs/{arxiv_id}"
            references.append({
                "url": url,
                "type": "arxiv",
                "title": f"arXiv:{arxiv_id}",
            })

        # HuggingFace链接
        hf_pattern = r'https?://huggingface\.co/([\w\-\.]+)/([\w\-\.]+)'
        for match in re.finditer(hf_pattern, text):
            url = match.group(0)
            references.append({
                "url": url,
                "type": "huggingface",
                "title": f"{match.group(1)}/{match.group(2)}",
            })

        # 去重
        seen = set()
        unique_refs = []
        for ref in references:
            if ref["url"] not in seen:
                seen.add(ref["url"])
                unique_refs.append(ref)

        return WorkerOutput(
            success=True,
            data={"references": unique_refs},
        )
