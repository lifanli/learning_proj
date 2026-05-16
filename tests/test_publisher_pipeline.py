"""新增的出版链回归测试"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.progress import reset_progress_reporter, set_progress_reporter
from src.core.llm_client import LLMClient
from src.core.material_store import Material, MaterialStore
from src.core.worker import WorkerInput
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

    def test_fallback_outline_groups_materials_and_splits_long_sources(self):
        planner = object.__new__(BookPlanner)
        planner.config = {
            "publisher": {
                "fallback_max_sections_per_chapter": 3,
                "fallback_long_material_chunk_chars": 1000,
            }
        }
        summaries = [
            {
                "id": f"m{i}",
                "summary": f"[web] FlashAttention inference material {i}",
                "title": f"FlashAttention inference material {i}",
                "source_type": "web",
                "tags": ["inference"],
                "content_chars": 500,
            }
            for i in range(7)
        ]
        summaries.append({
            "id": "long",
            "summary": "[arxiv] Long PEFT survey",
            "title": "PEFT A2Z long survey",
            "source_type": "arxiv",
            "tags": ["fine-tuning"],
            "content_chars": 2500,
        })

        outline = planner._fallback_outline("大模型全栈工程师", summaries)

        assert outline.metadata["fallback"] is True
        assert len(outline.chapters) > 1
        assert all(len(chapter["sections"]) <= 3 for chapter in outline.chapters)
        sliced_sections = [
            section
            for chapter in outline.chapters
            for section in chapter["sections"]
            if section.get("material_slices")
        ]
        assert len(sliced_sections) == 3
        assert sliced_sections[0]["material_slices"][0]["id"] == "long"

    def test_fallback_outline_limits_single_publish_batch(self):
        planner = object.__new__(BookPlanner)
        planner.config = {
            "publisher": {
                "fallback_max_materials": 5,
                "fallback_max_sections_per_chapter": 3,
            }
        }
        summaries = [
            {
                "id": f"m{i}",
                "summary": f"[web] material {i}",
                "title": f"material {i}",
                "source_type": "web",
                "tags": [],
                "content_chars": 1000,
            }
            for i in range(9)
        ]

        outline = planner._fallback_outline("批次测试", summaries)
        assigned = [
            material_id
            for chapter in outline.chapters
            for section in chapter["sections"]
            for material_id in section["material_ids"]
        ]

        assert len(assigned) == 5
        assert len(outline.metadata["deferred_materials"]) == 4
        assert outline.metadata["selected_materials"] == 5


class TestPublisherAgentMaterialSlices:
    def test_retrieve_materials_applies_content_slices(self, tmp_path):
        store = MaterialStore(str(tmp_path / "materials"))
        material_id = store.save(Material(
            source_url="https://example.com/long",
            source_type="web",
            title="Long Material",
            content="0123456789" * 20,
        ))
        agent = object.__new__(PublisherAgent)
        agent.store = store

        materials = agent._retrieve_materials(
            [material_id],
            material_slices=[{"id": material_id, "start": 10, "end": 30, "part": 1, "total_parts": 4}],
        )

        assert len(materials) == 1
        assert materials[0]["content"] == ("0123456789" * 20)[10:30]
        assert materials[0]["metadata"]["content_slice"]["part"] == 1


class TestSectionWriterChunking:
    def test_split_material_content_produces_multiple_chunks(self):
        content = "\n\n".join([f"段落{i}: " + ("内容" * 300) for i in range(6)])

        chunks = SectionWriter._split_material_content(content, chunk_chars=1200, overlap_chars=100)

        assert len(chunks) > 1
        assert all(chunk.strip() for chunk in chunks)

    def test_write_chunk_retries_truncated_output(self):
        writer = object.__new__(SectionWriter)
        calls = []

        def fake_llm_call(prompt, **kwargs):
            calls.append(prompt)
            if len(calls) == 1:
                raise RuntimeError("LLM response was truncated by output/context limit: length")
            return "## 重写后的完整分稿\n\n关键内容已经保留。"

        writer.llm_call = fake_llm_call

        draft = writer._write_chunk(
            system_prompt="system",
            chapter_title="章",
            section_title="节",
            outline_text="- 大纲",
            chunk="素材内容" * 200,
            chunk_index=1,
            chunk_count=1,
            images_text="",
            code_text="",
            min_section_words=100,
            max_section_words=1000,
            max_tokens=800,
        )

        assert "重写后的完整分稿" in draft
        assert len(calls) == 2
        assert "重要重试要求" in calls[1]

    def test_polish_truncation_keeps_merged_text(self):
        writer = object.__new__(SectionWriter)
        writer.llm_call = MagicMock(side_effect=RuntimeError(
            "LLM response was truncated by output/context limit: length"
        ))

        merged = "## 已合并正文\n\n这些内容不能丢。"
        result = writer._polish_section(
            merged_text=merged,
            system_prompt="system",
            chapter_title="章",
            section_title="节",
            outline_text="- 大纲",
            images_text="",
            code_text="",
            min_section_words=100,
            max_section_words=1000,
            max_tokens=800,
        )

        assert result == merged

    def test_execute_direct_assembles_many_chunks(self):
        writer = object.__new__(SectionWriter)
        writer.config = {
            "publisher": {
                "writer_chunk_chars": 100,
                "writer_overlap_chars": 0,
                "writer_partial_max_tokens": 800,
                "writer_merge_max_tokens": 800,
                "writer_polish_max_tokens": 800,
                "writer_direct_assemble_chunk_threshold": 1,
                "min_section_words": 50,
                "max_section_words": 500,
            }
        }
        writer.llm_call = MagicMock(return_value="## 分段正文\n\n这里是详细解释。")

        output = writer.execute(WorkerInput(
            content="\n\n".join(["素材段落" * 30 for _ in range(4)]),
            metadata={"chapter_title": "章", "section_title": "节"},
            extra={"outline": ["大纲"], "content_type": "default"},
        ))

        assert output.success is True
        assert "分段精读" in output.content
        assert "direct_assembled_from_many_chunks" in output.data["quality_flags"]


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
        agent._preflight_llm = MagicMock()
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

    @pytest.mark.asyncio
    async def test_publish_book_fails_fast_when_llm_preflight_fails(self, tmp_path):
        agent = object.__new__(PublisherAgent)
        agent.config = {"publisher": {"max_concurrent_sections": 1}}
        agent.kb_root = str(tmp_path)
        agent._preflight_llm = MagicMock(side_effect=RuntimeError("401 auth failed"))
        agent.plan_book = MagicMock()

        result = await agent.publish_book("Test Book", output_dir=str(tmp_path / "out"))

        assert result["status"] == "error"
        assert "出版前 LLM 连通性检查失败" in result["error"]
        agent.plan_book.assert_not_called()
