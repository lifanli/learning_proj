from types import SimpleNamespace

from src.core.material_store import Material
from src.core.worker import WorkerOutput, WorkerInput
from src.core.task_engine import TaskDAG, TaskNode, TaskStatus
from src.student.material_pipeline import (
    MaterialProcessingPipeline,
    CompletenessChecker,
    QualityScorer,
    PublishReadinessMarker,
)


class TestCompletenessChecker:
    def test_marks_missing_core_fields_and_empty_lists(self):
        material = Material(title="", content="short", tags=[], terms=[])

        result = CompletenessChecker().evaluate(material)

        assert result["is_complete"] is False
        assert "missing_title" in result["missing_fields"]
        assert "content_too_short" in result["missing_fields"]
        assert "missing_tags" in result["missing_fields"]
        assert "missing_terms" in result["missing_fields"]


class TestQualityScorer:
    def test_scores_material_and_adds_flags(self):
        material = Material(
            title="Transformer 教程",
            content="这是一段较短的内容",
            tags=[],
            terms=["Transformer"],
            references=[],
            code_blocks=[],
            images=[],
        )
        completeness = {"is_complete": False, "missing_fields": ["missing_tags", "content_too_short"]}

        result = QualityScorer().evaluate(material, completeness)

        assert result["score"] < 60
        assert "missing_tags" in result["flags"]
        assert "content_too_short" in result["flags"]


class TestPublishReadinessMarker:
    def test_blocks_publish_when_score_low_or_incomplete(self):
        material = Material(title="坏素材", content="short")

        result = PublishReadinessMarker(min_score=60).evaluate(
            material,
            completeness={"is_complete": False, "missing_fields": ["content_too_short"]},
            quality={"score": 35, "flags": ["content_too_short"]},
        )

        assert result["ready_for_publish"] is False
        assert "content_too_short" in result["reasons"]


class TestMaterialProcessingPipeline:
    def test_build_enrich_dag_exposes_three_stage_module_groups(self):
        material = Material(id="mat001", title="Test", content="English content", source_url="https://example.com")
        fetch_output = WorkerOutput(
            success=True,
            data={
                "images": [{"url": "https://example.com/a.png", "alt": "diagram"}],
                "code_blocks": [],
            },
        )

        pipeline = MaterialProcessingPipeline(
            workers={
                "image": object(),
                "code": object(),
                "term": object(),
                "ref": object(),
                "translator": object(),
                "tagger": object(),
            },
            config={"student": {"image_download": True, "image_interpret": False}},
            image_save_dir="/tmp/mat001/images",
        )

        dag = pipeline.build_enrich_dag(material, fetch_output)

        assert dag.name == "enrich_mat001"
        assert pipeline.extraction_modules == ["image", "code", "ref"]
        assert pipeline.semantic_modules == ["term", "translator", "tagger"]
        assert pipeline.quality_modules == ["completeness", "quality", "publish_readiness"]
        assert {node.name for node in dag.nodes.values()} == {"image", "code", "term", "ref", "translator", "tagger"}

    def test_apply_results_updates_material_and_quality_metadata(self):
        material = Material(id="mat002", title="Example", content="English content")
        dag = TaskDAG(name="enrich_mat002")

        def add_node(name, output):
            node = TaskNode(name=name, input_data=WorkerInput())
            node.status = TaskStatus.COMPLETED
            node.output = output
            dag.add_node(node)

        add_node("code", WorkerOutput(success=True, data={"code_blocks": [{"language": "python", "code": "print(1)", "comment": "打印"}]}))
        add_node("term", WorkerOutput(success=True, data={"terms": ["Transformer", "Attention"]}))
        add_node("ref", WorkerOutput(success=True, data={"references": [{"url": "https://arxiv.org/abs/2501.00001", "type": "arxiv", "title": "paper"}]}))
        add_node("translator", WorkerOutput(success=True, content="中文内容", data={"translated": True, "language": "zh"}))
        add_node("tagger", WorkerOutput(success=True, data={"tags": ["大语言模型", "Transformer"]}))
        add_node("image", WorkerOutput(success=True, data={"images": [{"url": "https://example.com/fig.png", "description": "架构图"}]}))

        pipeline = MaterialProcessingPipeline(workers={}, config={}, image_save_dir="/tmp")
        updated = pipeline.apply_results(material, dag)

        assert updated.content == "中文内容"
        assert updated.language == "zh"
        assert updated.tags == ["大语言模型", "Transformer"]
        assert updated.terms == ["Transformer", "Attention"]
        assert updated.metadata["processing"]["quality"]["score"] >= 0
        assert "ready_for_publish" in updated.metadata["processing"]


class TestStudentAgentPipelineIntegration:
    def test_student_agent_delegates_to_material_pipeline(self, mock_settings, monkeypatch):
        from src.student.student_agent import StudentAgent

        agent = StudentAgent()
        material = Material(id="mat003", title="Title", content="English content")
        fetch_output = WorkerOutput(success=True, data={"images": [], "code_blocks": []})

        captured = {}

        class FakePipeline:
            def __init__(self, **kwargs):
                captured["kwargs"] = kwargs

            def build_enrich_dag(self, mat, output):
                captured["build"] = (mat.id, output.success)
                return SimpleNamespace(name="fake_dag")

            def apply_results(self, mat, dag):
                mat.metadata["pipeline"] = dag.name
                return mat

        async def fake_execute(dag):
            captured["executed"] = dag.name
            return dag

        monkeypatch.setattr("src.student.student_agent.MaterialProcessingPipeline", FakePipeline)
        agent.engine.execute = fake_execute

        import asyncio
        updated = asyncio.run(agent._enrich_material(material, fetch_output))

        assert captured["build"] == ("mat003", True)
        assert captured["executed"] == "fake_dag"
        assert updated.metadata["pipeline"] == "fake_dag"
