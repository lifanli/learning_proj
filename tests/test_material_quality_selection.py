from src.core.material_store import Material, MaterialStore
from src.publisher_v2.book_planner import BookPlanner


def test_material_store_persists_processing_quality_metadata(tmp_path):
    store = MaterialStore(str(tmp_path / "materials"))
    material = Material(
        source_url="https://example.com/a",
        source_type="web",
        title="高质量素材",
        content="这是一段足够长的中文内容，用来验证质量元数据会被完整持久化。" * 5,
        metadata={
            "processing": {
                "quality": {"score": 92, "grade": "A", "flags": []},
                "ready_for_publish": {"ready_for_publish": True, "reasons": []},
            }
        },
    )

    material_id = store.save(material)
    loaded = store.get(material_id)
    queried = store.query(limit=10)[0]

    assert loaded is not None
    assert loaded.metadata["processing"]["quality"]["score"] == 92
    assert loaded.metadata["processing"]["ready_for_publish"]["ready_for_publish"] is True
    assert queried.metadata["processing"]["quality"]["score"] == 92


def test_material_store_query_prefers_publish_ready_high_quality_materials(tmp_path):
    store = MaterialStore(str(tmp_path / "materials"))

    low = Material(
        source_url="https://example.com/low",
        source_type="web",
        title="低质量素材",
        content="低质量内容" * 10,
        metadata={
            "processing": {
                "quality": {"score": 35, "grade": "D", "flags": ["content_too_short"]},
                "ready_for_publish": {"ready_for_publish": False, "reasons": ["quality_score_below_threshold"]},
            }
        },
    )
    high = Material(
        source_url="https://example.com/high",
        source_type="web",
        title="高质量素材",
        content="高质量内容" * 50,
        metadata={
            "processing": {
                "quality": {"score": 95, "grade": "A", "flags": []},
                "ready_for_publish": {"ready_for_publish": True, "reasons": []},
            }
        },
    )

    store.save(low)
    store.save(high)

    results = store.query(limit=10)

    assert [mat.title for mat in results[:2]] == ["高质量素材", "低质量素材"]


def test_book_planner_summaries_prioritize_ready_materials(mock_settings):
    planner = BookPlanner()
    captured = {}

    def fake_plan(topic, summaries):
        captured["summaries"] = summaries
        return planner._fallback_outline(topic, summaries)

    planner._plan_with_llm = fake_plan

    ready = Material(
        id="m_ready",
        source_type="github",
        title="Ready Material",
        summary="high quality",
        tags=["agent"],
        metadata={
            "processing": {
                "quality": {"score": 91, "grade": "A", "flags": []},
                "ready_for_publish": {"ready_for_publish": True, "reasons": []},
            }
        },
    )
    not_ready = Material(
        id="m_not_ready",
        source_type="web",
        title="Not Ready Material",
        summary="needs work",
        tags=["agent"],
        metadata={
            "processing": {
                "quality": {"score": 45, "grade": "D", "flags": ["content_too_short"]},
                "ready_for_publish": {"ready_for_publish": False, "reasons": ["quality_score_below_threshold"]},
            }
        },
    )

    class FakeStore:
        def query(self, **kwargs):
            return [not_ready, ready]

    outline = planner.plan_book(FakeStore(), "Agent 系统")

    summaries = captured["summaries"]
    assert summaries[0]["id"] == "m_ready"
    assert "质量:91" in summaries[0]["summary"]
    assert "可出版" in summaries[0]["summary"]
    assert summaries[1]["id"] == "m_not_ready"
    assert outline.metadata["material_priority"][0]["id"] == "m_ready"
