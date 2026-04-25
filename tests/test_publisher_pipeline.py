"""新增的出版链回归测试"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.progress import reset_progress_reporter, set_progress_reporter
from src.core.llm_client import LLMClient
from src.publisher_v2.book_planner import BookOutline, BookPlanner
from src.publisher_v2.publisher_agent import PublisherAgent
from src.publisher_v2.workers.section_writer import SectionWriter


class TestLlmClientTruncation:
    def test_raise_if_truncated_length(self):
        try:
            LLMClient._raise_if_truncated("length")
            assert False, "expected RuntimeError"
        except RuntimeError as exc:
            assert "truncated" in str(exc)

    def test_raise_if_truncated_none(self):
        LLMClient._raise_if_truncated(None)


class TestBookPlannerCoverage:
    def test_ensure_all_materials_assigned_appends_missing(self):
        planner = object.__new__(BookPlanner)
        outline = BookOutline(
            title="测试书",
            description="",
            chapters=[
                {
                    "title": "第一章",
                    "sections": [
                        {"title": "1.1", "material_ids": ["m1"], "description": "a"},
                    ],
                }
            ],
            metadata={},
        )
        summaries = [
            {"id": "m1", "summary": "已分配素材"},
            {"id": "m2", "summary": "遗漏素材"},
        ]

        fixed = planner._ensure_all_materials_assigned(outline, summaries)

        assert len(fixed.chapters) == 2
        appendix = fixed.chapters[-1]
        assert appendix["title"] == "补充素材精读"
        assert appendix["sections"][0]["material_ids"] == ["m2"]
        assert fixed.metadata["coverage"]["auto_assigned_materials"] == 1


class TestSectionWriterChunking:
    def test_split_material_content_produces_multiple_chunks(self):
        content = "\n\n".join([f"段落{i}: " + ("内容" * 300) for i in range(6)])

        chunks = SectionWriter._split_material_content(content, chunk_chars=1200, overlap_chars=100)

        assert len(chunks) > 1
        assert all(chunk.strip() for chunk in chunks)


class TestPublisherAgentReport:
    def test_build_publish_report_marks_partial_on_missing_and_flags(self):
        agent = object.__new__(PublisherAgent)
        outline = BookOutline(title="书", description="", chapters=[], metadata={})
        assembled = [
            {
                "title": "第一章",
                "sections": [
                    {
                        "title": "1.1",
                        "quality": {"flags": ["too_short"]},
                    }
                ],
            }
        ]
        expected_sections = [{"chapter": "第一章", "section": "1.1", "file_path": "01/a.md"}]
        missing_sections = [{"chapter": "第一章", "section": "1.2", "reason": "撰写失败"}]

        report = agent._build_publish_report(
            outline=outline,
            assembled_chapters=assembled,
            expected_sections=expected_sections,
            missing_sections=missing_sections,
            warnings=["第一章/1.1: too_short"],
        )

        assert report["status"] == "partial"
        assert report["completed_sections"] == 1
        assert len(report["missing_sections"]) == 1
        assert report["quality_summary"][0]["flags"] == ["too_short"]

    @pytest.mark.asyncio
    async def test_publish_book_reports_chapter_progress(self, tmp_path):
        agent = object.__new__(PublisherAgent)
        agent.config = {"publisher": {"max_concurrent_sections": 1}}
        agent.kb_root = str(tmp_path)
        outline = BookOutline(
            title="Test Book",
            description="",
            chapters=[{"title": "Chapter 1", "sections": [{"title": "Section 1", "material_ids": ["m1"]}]}],
            metadata={},
        )
        agent.plan_book = MagicMock(return_value=outline)
        agent._collect_expected_sections = MagicMock(
            return_value=[{"chapter": "Chapter 1", "section": "Section 1", "file_path": "chapter/section.md"}]
        )
        agent._process_section = AsyncMock(return_value={"title": "Section 1", "content": "content", "warnings": []})
        agent._build_publish_report = MagicMock(
            return_value={"status": "success", "completed_sections": 1, "expected_sections": 1}
        )
        agent.assembler = MagicMock()
        agent.assembler.assemble.return_value = str(tmp_path / "Test Book")

        updates = []
        token = set_progress_reporter(lambda progress=None, message=None: updates.append((progress, message)))
        try:
            result = await agent.publish_book("Test Book", output_dir=str(tmp_path / "out"))
        finally:
            reset_progress_reporter(token)

        assert result["status"] == "success"
        assert any(message and "出版：目录规划完成" in message for _, message in updates)
        assert any(message and "出版：撰写章节 1/1" in message for _, message in updates)
        assert any(message == "出版：组装知识库文件" for _, message in updates)
