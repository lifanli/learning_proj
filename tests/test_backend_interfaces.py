import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from src.core.material_store import Material, MaterialStore
from src.core.progress import reset_progress_reporter, set_progress_reporter
from src.core.worker import WorkerOutput
from src.graph.pipeline import KnowledgePipeline
from src.publisher_v2.book_planner import BookOutline
from src.publisher_v2.publisher_agent import PublisherAgent
from src.student.curriculum_agent import CurriculumAgent
from src.student.student_agent import StudentAgent
from src.student.study_planner import StudyPlan
import src.core.worker as worker_module


def _reset_worker_config_cache():
    worker_module._config_cache = None
    worker_module._config_mtime = 0.0


def _write_project_settings(tmp_path: Path, monkeypatch, student=None, publisher=None):
    config_dir = tmp_path / "config"
    data_dir = tmp_path / "data"
    materials_dir = data_dir / "materials"
    kb_dir = tmp_path / "knowledge_base"

    config_dir.mkdir(parents=True, exist_ok=True)
    materials_dir.mkdir(parents=True, exist_ok=True)
    kb_dir.mkdir(parents=True, exist_ok=True)

    settings = {
        "llm": {
            "provider": "openai",
            "api_key_env": "TEST_API_KEY",
            "base_url": "https://localhost/v1",
            "model": "test-model",
            "enable_thinking": False,
        },
        "models": {"fast": "test-fast", "deep": "test-deep", "vision": "test-vision"},
        "paths": {
            "knowledge_base": str(kb_dir),
            "data": str(data_dir),
            "materials": str(materials_dir),
        },
        "language": {
            "target": "Chinese",
            "translation_prompt": "Translate to Chinese.",
        },
        "student": {
            "max_concurrent_fetches": 2,
            "image_download": False,
            "image_interpret": False,
            "follow_references": False,
            "max_reference_depth": 1,
        },
        "publisher": {
            "min_section_words": 10,
            "max_section_words": 500,
            "include_code_annotations": False,
            "include_images": False,
            "quality_review": False,
            "max_context_chars": 1000,
            "max_concurrent_sections": 2,
        },
    }
    if student:
        settings["student"].update(student)
    if publisher:
        settings["publisher"].update(publisher)

    with open(config_dir / "settings.yaml", "w", encoding="utf-8") as f:
        yaml.dump(settings, f, allow_unicode=True)
    with open(config_dir / "curriculum_registry.yaml", "w", encoding="utf-8") as f:
        yaml.dump({"sources": []}, f, allow_unicode=True)

    monkeypatch.setenv("TEST_API_KEY", "fake-key")
    monkeypatch.chdir(tmp_path)
    _reset_worker_config_cache()

    return {
        "config_dir": config_dir,
        "data_dir": data_dir,
        "materials_dir": materials_dir,
        "kb_dir": kb_dir,
    }


class _FakeRAG:
    def __init__(self):
        self.inserted = []
        self.queries = []

    async def insert_text(self, text):
        self.inserted.append(text)

    async def query(self, query, mode="hybrid"):
        self.queries.append((query, mode))
        return "相关知识摘要"


class _FakeTranslator:
    def translate(self, text):
        return f"ZH:{text}"


class _FakePlanner:
    def plan(self, topic, summary):
        return "01_测试分类"


class _FakeFactChecker:
    def check(self, content, source, rag_content):
        return {"passed": True, "corrected_content": content}


class _FakeEditor:
    def __init__(self, kb_root):
        self.kb_root = str(kb_root)
        self.rag = _FakeRAG()
        self.translator = _FakeTranslator()
        self.planner = _FakePlanner()
        self.fact_checker = _FakeFactChecker()

    def _compose_article(self, translated_topic, translated_rag, source, translated_summary):
        return (
            f"# {translated_topic}\n\n"
            f"来源: {source}\n\n"
            f"摘要: {translated_summary}\n\n"
            f"内容: {translated_rag}\n"
        )


def test_curriculum_agent_interface_approve_update_and_progress(tmp_path, monkeypatch):
    paths = _write_project_settings(tmp_path, monkeypatch)
    agent = CurriculumAgent()
    curriculum_path = paths["config_dir"] / "curriculum.yaml"

    curriculum = {
        "goal": "LLM 全栈",
        "depth": "quick",
        "status": "draft",
        "domains": [
            {
                "name": "基础",
                "priority": 1,
                "topics": [
                    {"name": "Transformer", "status": "pending", "known_sources": [], "discovered_sources": []},
                    {"name": "Tokenizer", "status": "done", "known_sources": [], "discovered_sources": []},
                ],
            }
        ],
    }
    agent.save(curriculum, str(curriculum_path))

    agent.approve(str(curriculum_path))
    agent.update_topic_status("基础", "Transformer", "studying", str(curriculum_path))
    updated = agent.load(str(curriculum_path))
    progress = agent.get_progress(str(curriculum_path))

    assert updated["status"] == "approved"
    assert updated["domains"][0]["topics"][0]["status"] == "studying"
    assert progress == {"total": 2, "done": 1, "studying": 1, "pending": 0}


@pytest.mark.asyncio
async def test_student_agent_study_course_interface(tmp_path, monkeypatch):
    _write_project_settings(tmp_path, monkeypatch)
    agent = StudentAgent()

    plan = StudyPlan(
        source_type="course",
        root_url="https://example.com/course",
        title="测试课程",
        pages=[
            {"url": "https://example.com/course/1", "title": "第一课", "order": 0},
            {"url": "https://example.com/course/2", "title": "第二课", "order": 1},
        ],
    )
    agent.planner.plan_course = MagicMock(return_value=plan)
    agent._process_course_page = AsyncMock(side_effect=["m_page_1", "m_page_2"])
    agent._follow_references = AsyncMock()

    result = await agent.study_course("https://example.com/course", max_pages=10)
    course_root = agent.store.get(result["parent_id"])

    assert result["title"] == "测试课程"
    assert result["material_ids"] == ["m_page_1", "m_page_2"]
    assert result["total_pages"] == 2
    assert course_root is not None
    assert course_root.source_type == "course"
    agent._follow_references.assert_not_called()


@pytest.mark.asyncio
async def test_student_agent_study_github_interface(tmp_path, monkeypatch):
    _write_project_settings(tmp_path, monkeypatch)
    agent = StudentAgent()

    material = Material(
        source_url="https://github.com/example/repo",
        source_type="github",
        title="Example Repo",
        content="repository content",
    )
    agent.github_analyzer.run = MagicMock(return_value=WorkerOutput(success=True, materials=[material]))
    agent.tagger.run = MagicMock(return_value=WorkerOutput(success=True, data={"tags": ["agent", "llm"]}))

    result = await agent.study_github("https://github.com/example/repo")
    stored = agent.store.get(result["material_id"])

    assert result["title"] == "Example Repo"
    assert stored is not None
    assert stored.source_type == "github"
    assert stored.tags == ["agent", "llm"]


@pytest.mark.asyncio
async def test_student_agent_study_arxiv_interface(tmp_path, monkeypatch):
    _write_project_settings(tmp_path, monkeypatch)
    agent = StudentAgent()

    material = Material(
        source_url="https://arxiv.org/abs/2501.00001",
        source_type="arxiv",
        title="Paper Title",
        content="original english content",
    )
    agent.paper_analyzer.run = MagicMock(return_value=WorkerOutput(success=True, materials=[material]))
    agent.translator.run = MagicMock(return_value=WorkerOutput(success=True, content="中文内容", data={"translated": True}))
    agent.tagger.run = MagicMock(return_value=WorkerOutput(success=True, data={"tags": ["paper", "research"]}))

    result = await agent.study_arxiv("https://arxiv.org/abs/2501.00001")
    stored = agent.store.get(result["material_id"])

    assert result["title"] == "Paper Title"
    assert stored is not None
    assert stored.language == "zh"
    assert stored.content == "中文内容"
    assert stored.tags == ["paper", "research"]


@pytest.mark.asyncio
async def test_student_agent_study_topic_interface_dispatches_resources(tmp_path, monkeypatch):
    _write_project_settings(tmp_path, monkeypatch)
    agent = StudentAgent()

    resources = [
        {"url": "https://github.com/example/repo", "type": "github", "title": "repo"},
        {"url": "https://arxiv.org/abs/2501.00001", "type": "arxiv", "title": "paper"},
        {"url": "https://example.com/course", "type": "course", "title": "course"},
        {"url": "https://example.com/doc", "type": "web", "title": "doc"},
    ]

    agent.study_github = AsyncMock(return_value={"material_id": "m_github"})
    agent.study_arxiv = AsyncMock(return_value={"material_id": "m_arxiv"})
    agent.study_course = AsyncMock(return_value={"material_ids": ["m_course_1", "m_course_2"]})
    agent._study_web_page = AsyncMock(return_value={"material_id": "m_web"})

    with patch("src.student.topic_explorer.TopicExplorer.__init__", return_value=None), \
         patch("src.student.topic_explorer.TopicExplorer.explore", return_value=resources):
        result = await agent.study_topic("LLM 全栈", search_queries=["Transformer"], max_resources=6)

    assert result["title"] == "LLM 全栈"
    assert result["resources_found"] == 4
    assert result["errors"] == []
    assert result["material_ids"] == ["m_github", "m_arxiv", "m_course_1", "m_course_2", "m_web"]


@pytest.mark.asyncio
async def test_student_agent_study_curriculum_interface_updates_curriculum_status(tmp_path, monkeypatch):
    paths = _write_project_settings(tmp_path, monkeypatch)
    curriculum_path = paths["config_dir"] / "curriculum.yaml"

    curriculum = {
        "goal": "LLM 全栈",
        "depth": "quick",
        "status": "approved",
        "domains": [
            {
                "name": "基础",
                "priority": 1,
                "topics": [
                    {
                        "name": "Transformer",
                        "status": "pending",
                        "search_queries": ["Transformer tutorial"],
                        "known_sources": [],
                        "discovered_sources": [],
                    },
                    {
                        "name": "Tokenizer",
                        "status": "done",
                        "search_queries": [],
                        "known_sources": [],
                        "discovered_sources": [],
                    },
                ],
            }
        ],
    }
    with open(curriculum_path, "w", encoding="utf-8") as f:
        yaml.dump(curriculum, f, allow_unicode=True, sort_keys=False)

    agent = StudentAgent()
    agent.study_topic = AsyncMock(return_value={"material_ids": [], "errors": [], "resources_found": 1})

    updates = []
    token = set_progress_reporter(lambda progress=None, message=None: updates.append((progress, message)))
    try:
        result = await agent.study_curriculum(str(curriculum_path))
    finally:
        reset_progress_reporter(token)

    with open(curriculum_path, "r", encoding="utf-8") as f:
        updated = yaml.safe_load(f)

    assert result == {"completed": 1, "failed": 0, "skipped": 1, "total": 2}
    assert updated["status"] == "completed"
    topics = updated["domains"][0]["topics"]
    assert topics[0]["status"] == "done"
    assert topics[1]["status"] == "done"
    assert any(message and "自动学习：学习 1/2" in message for _, message in updates)
    assert any(message and "自动学习：已处理 1/2" in message for _, message in updates)


@pytest.mark.asyncio
async def test_student_agent_study_curriculum_allows_completed_status(tmp_path, monkeypatch):
    paths = _write_project_settings(tmp_path, monkeypatch)
    curriculum_path = paths["config_dir"] / "curriculum.yaml"

    curriculum = {
        "goal": "LLM 全栈",
        "depth": "quick",
        "status": "completed",
        "domains": [
            {
                "name": "基础",
                "priority": 1,
                "topics": [
                    {
                        "name": "Transformer",
                        "status": "done",
                        "search_queries": [],
                        "known_sources": [],
                        "discovered_sources": [],
                    }
                ],
            }
        ],
    }
    with open(curriculum_path, "w", encoding="utf-8") as f:
        yaml.dump(curriculum, f, allow_unicode=True, sort_keys=False)

    agent = StudentAgent()
    agent.study_topic = AsyncMock()

    result = await agent.study_curriculum(str(curriculum_path))

    assert result == {"completed": 0, "failed": 0, "skipped": 1, "total": 1}
    agent.study_topic.assert_not_called()


def test_publisher_agent_plan_book_interface(tmp_path, monkeypatch):
    _write_project_settings(tmp_path, monkeypatch)
    agent = PublisherAgent()
    outline = BookOutline(title="LLM 教程", description="desc", chapters=[])
    agent.planner.plan_book = MagicMock(return_value=outline)

    result = agent.plan_book("LLM 教程", parent_id="p1", tags=["llm"])

    assert result.title == "LLM 教程"
    agent.planner.plan_book.assert_called_once_with(agent.store, "LLM 教程", "p1", ["llm"])


@pytest.mark.asyncio
async def test_publisher_agent_publish_chapter_interface(tmp_path, monkeypatch):
    _write_project_settings(tmp_path, monkeypatch)
    agent = PublisherAgent()
    outline = BookOutline(
        title="LLM 教程",
        description="desc",
        chapters=[{"title": "第1章", "sections": []}],
    )

    agent.plan_book = MagicMock(return_value=outline)
    agent.publish_book = AsyncMock(return_value={"status": "success", "title": "LLM 教程"})

    result = await agent.publish_chapter("LLM 教程", chapter_index=0, parent_id="p1")
    error_result = await agent.publish_chapter("LLM 教程", chapter_index=3, parent_id="p1")

    assert result["status"] == "success"
    agent.publish_book.assert_awaited_once_with(topic="LLM 教程", parent_id="p1")
    assert error_result["status"] == "error"
    assert "超出范围" in error_result["error"]


@pytest.mark.asyncio
async def test_knowledge_pipeline_process_interface(tmp_path):
    kb_root = tmp_path / "knowledge_base"
    kb_root.mkdir(parents=True, exist_ok=True)
    editor = _FakeEditor(kb_root)
    pipeline = KnowledgePipeline(editor, db_path=str(tmp_path / "data" / "pipeline_checkpoints.db"))

    state = await pipeline.process(
        content="这是一段原始内容",
        source="https://example.com/article",
        topic="LLM 综述",
    )

    assert state.status == "completed"
    assert state.current_step == 8
    assert Path(state.output_path).exists()
    assert editor.rag.inserted
    assert editor.rag.queries
    with open(state.output_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "ZH:LLM 综述" in content
    assert "来源: https://example.com/article" in content
