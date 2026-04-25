"""
目录结构组装Worker (BookAssembler)
====================================
将所有章节组装为完整的知识库输出（目录 + 独立文件）。
"""

import json
import os
import re
from typing import Dict, List

from src.core.worker import BaseWorker, WorkerSpec, WorkerInput, WorkerOutput
from src.utils.logger import logger


class BookAssembler(BaseWorker):
    """目录结构组装输出Worker"""

    def __init__(self):
        super().__init__(WorkerSpec(
            name="BookAssembler",
            description="组装知识库输出目录结构",
            model_level="fast",
            max_retries=1,
        ))

    def execute(self, input_data: WorkerInput) -> WorkerOutput:
        """不直接使用execute，用assemble方法替代"""
        return WorkerOutput(success=True)

    def assemble(
        self,
        output_dir: str,
        book_title: str,
        chapters: List[Dict],
        report: Dict = None,
    ) -> str:
        """
        组装知识库输出。

        Args:
            output_dir: 输出根目录 (如 knowledge_base/03_LLM课程)
            book_title: 书名
            chapters: 章节和小节内容
            report: 出版质量报告

        Returns:
            输出目录路径
        """
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"[BookAssembler] 开始组装: {book_title} -> {output_dir}")

        report = report or {}
        toc_lines = self._build_readme_header(book_title, report)
        output_files = []

        for ch_idx, chapter in enumerate(chapters):
            ch_title = chapter.get("title", f"第{ch_idx+1}章")
            ch_dir_name = self._safe_filename(ch_title)
            ch_dir = os.path.join(output_dir, f"{ch_idx+1:02d}_{ch_dir_name}")
            os.makedirs(ch_dir, exist_ok=True)

            toc_lines.append(f"\n## {ch_title}\n")

            for sec_idx, section in enumerate(chapter.get("sections", [])):
                sec_title = section.get("title", f"{ch_idx+1}.{sec_idx+1}")
                sec_content = section.get("content", "")
                quality = section.get("quality", {})

                filename = f"{sec_idx+1:02d}_{self._safe_filename(sec_title)}.md"
                file_path = os.path.join(ch_dir, filename)

                full_content = self._build_section_file(sec_title, sec_content, quality)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(full_content)

                rel_path = os.path.relpath(file_path, output_dir).replace("\\", "/")
                flags = quality.get("flags", [])
                flag_text = f"  _{', '.join(flags)}_" if flags else ""
                toc_lines.append(f"- [{sec_title}]({rel_path}){flag_text}")
                output_files.append(file_path)

        toc_path = os.path.join(output_dir, "README.md")
        with open(toc_path, "w", encoding="utf-8") as f:
            f.write("\n".join(toc_lines).rstrip() + "\n")
        output_files.insert(0, toc_path)

        report_path = os.path.join(output_dir, "publish_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        output_files.append(report_path)

        logger.info(
            f"[BookAssembler] 组装完成: {len(output_files)}个文件 -> {output_dir}"
        )
        return output_dir

    @staticmethod
    def _build_readme_header(book_title: str, report: Dict) -> List[str]:
        lines = [f"# {book_title}\n"]
        status = report.get("status", "success")
        expected = report.get("expected_sections", 0)
        completed = report.get("completed_sections", 0)
        missing = report.get("missing_sections", [])
        warnings = report.get("warnings", [])

        lines.append("## 出版质量概览\n")
        lines.append(f"- 状态: **{status}**")
        lines.append(f"- 完成小节: **{completed}/{expected}**")
        lines.append(f"- 缺失小节: **{len(missing)}**")
        lines.append(f"- 质量提醒: **{len(warnings)}**")

        if missing:
            lines.append("\n### 缺失小节")
            for item in missing[:20]:
                lines.append(f"- {item.get('chapter', '')} / {item.get('section', '')}: {item.get('reason', '')}")

        if warnings:
            lines.append("\n### 质量提醒")
            for warning in warnings[:30]:
                lines.append(f"- {warning}")

        lines.append("\n## 目录")
        return lines

    @staticmethod
    def _build_section_file(sec_title: str, sec_content: str, quality: Dict) -> str:
        metadata_lines = []
        if quality:
            metadata_lines.append("> 出版质量信息")
            metadata_lines.append(f"> - 字符数: {quality.get('chars', 0)}")
            metadata_lines.append(f"> - 估算长度单位: {quality.get('estimated_length_units', 0)}")
            if quality.get("chunk_count"):
                metadata_lines.append(f"> - 写作分块: {quality.get('chunk_count')}")
            if quality.get("flags"):
                metadata_lines.append(f"> - 风险标记: {', '.join(quality.get('flags'))}")
            metadata_lines.append("")

        prefix = f"# {sec_title}\n\n"
        return prefix + "\n".join(metadata_lines) + sec_content.rstrip() + "\n"

    def _safe_filename(self, title: str, max_len: int = 40) -> str:
        """将标题转为安全的文件名"""
        title = re.sub(r'^第?\d+[章节\.]\s*', '', title)
        safe = re.sub(r'[<>:"/\\|?*]', '', title)
        safe = safe.strip().replace(" ", "_")
        if len(safe) > max_len:
            safe = safe[:max_len]
        return safe or "untitled"
