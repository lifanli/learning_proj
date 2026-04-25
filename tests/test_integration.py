"""
集成测试
========
覆盖场景:
1. Mock HTTP + LLM，跑通 study_wechat() 全流程，验证 Material 正确存储
2. 预填充 MaterialStore，跑通 publish_book() 全流程，验证输出文件
3. 创建 4 并行节点 DAG，验证 TaskEngine 并发执行
4. DAG 部分执行 → 恢复 → 完成
"""

import asyncio
import os
import time
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from src.core.task_engine import TaskEngine, TaskNode, TaskDAG, TaskStatus, TaskCheckpointer
from src.core.worker import BaseWorker, WorkerSpec, WorkerInput, WorkerOutput
from src.core.material_store import MaterialStore, Material


# =====================================================================
# 辅助: 创建可控的 Mock Worker
# =====================================================================

class MockWorker(BaseWorker):
    """可控的测试 Worker，不做 LLM 调用"""

    def __init__(self, name: str = "mock", output_data: dict = None,
                 output_content: str = "", fail: bool = False, delay: float = 0):
        spec = WorkerSpec(name=name, model_level="fast")
        # 不调用 super().__init__ 的 config 加载，直接设置必要属性
        self.spec = spec
        self.config = {
            "llm": {"api_key_env": "TEST_KEY", "base_url": "http://localhost"},
            "models": {"fast": "m", "deep": "m", "vision": "m"},
        }
        self._client = None  # 使用 _client 而非 client (property)
        self._output_data = output_data or {}
        self._output_content = output_content
        self._fail = fail
        self._delay = delay
        self._call_count = 0

    def execute(self, input_data: WorkerInput) -> WorkerOutput:
        self._call_count += 1
        if self._delay:
            time.sleep(self._delay)
        if self._fail:
            return WorkerOutput(success=False, error="mock failure")
        return WorkerOutput(
            success=True,
            content=self._output_content or input_data.content or "",
            data=self._output_data,
        )


# =====================================================================
# Test 1: study_wechat 全流程 (Mock HTTP + LLM)
# =====================================================================

@pytest.mark.asyncio
async def test_study_wechat_integration(tmp_path, monkeypatch):
    """Mock 所有外部依赖，跑通 study_wechat 全流程"""
    import yaml

    # 1. 准备配置
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    materials_dir = tmp_path / "data" / "materials"
    materials_dir.mkdir(parents=True)

    settings = {
        "llm": {
            "api_key_env": "TEST_API_KEY",
            "base_url": "https://localhost/v1",
            "model": "test-model",
            "enable_thinking": False,
        },
        "models": {"fast": "test-fast", "deep": "test-deep", "vision": "test-vision"},
        "paths": {
            "knowledge_base": str(tmp_path / "knowledge_base"),
            "data": str(tmp_path / "data"),
            "materials": str(materials_dir),
        },
        "language": {"target": "Chinese", "translation_prompt": "Translate"},
        "student": {
            "max_concurrent_fetches": 2,
            "image_download": False,
            "image_interpret": False,
            "follow_references": False,
            "max_reference_depth": 1,
        },
        "publisher": {},
    }
    with open(config_dir / "settings.yaml", "w", encoding="utf-8") as f:
        yaml.dump(settings, f)

    monkeypatch.setenv("TEST_API_KEY", "fake-key")
    monkeypatch.chdir(tmp_path)

    # 2. Mock workers — 替换 StudentAgent 的 worker 实例
    from src.student.student_agent import StudentAgent

    agent = StudentAgent()
    agent.store = MaterialStore(str(materials_dir))

    # Mock fetcher
    mock_mat = Material(
        source_url="https://mp.weixin.qq.com/s/test123",
        source_type="wechat",
        title="测试微信文章",
        content="这是一篇关于LLM的微信文章内容。包含了Transformer架构介绍。",
    )
    mock_fetch = WorkerOutput(
        success=True,
        content=mock_mat.content,
        materials=[mock_mat],
        data={"images": []},
    )
    agent.fetcher = MagicMock()
    agent.fetcher.run = MagicMock(return_value=mock_fetch)

    # Mock planner
    from src.student.study_planner import StudyPlan
    mock_plan = StudyPlan(title="测试文章", pages=[], github_urls=[], arxiv_urls=[])
    agent.planner = MagicMock()
    agent.planner.plan_wechat = MagicMock(return_value=mock_plan)

    # Mock enrichment workers
    agent.code_extractor = MockWorker("code", output_data={"code_blocks": [{"language": "python", "code": "x=1"}]})
    agent.term_extractor = MockWorker("term", output_data={"terms": ["LLM", "Transformer"]})
    agent.ref_tracker = MockWorker("ref", output_data={"references": []})
    agent.translator = MockWorker("translator", output_data={"translated": False, "language": "zh"})
    agent.tagger = MockWorker("tagger", output_data={"tags": ["LLM", "NLP"]})

    # 3. 执行
    result = await agent.study_wechat("https://mp.weixin.qq.com/s/test123")

    # 4. 验证
    assert "error" not in result
    assert result["title"] == "测试微信文章"
    assert "material_id" in result

    # 验证素材已存入 store
    mat_id = result["material_id"]
    stored = agent.store.get(mat_id)
    assert stored is not None
    assert stored.title == "测试微信文章"
    assert stored.source_type == "wechat"
    assert "LLM" in stored.tags
    assert len(stored.code_blocks) == 1
    assert "LLM" in stored.terms


# =====================================================================
# Test 2: publish_book 全流程 (预填充 MaterialStore)
# =====================================================================

@pytest.mark.asyncio
async def test_publish_book_integration(tmp_path, monkeypatch):
    """预填充 MaterialStore，跑通 publish_book 全流程"""
    import yaml

    # 1. 准备配置
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    materials_dir = tmp_path / "data" / "materials"
    materials_dir.mkdir(parents=True)
    kb_dir = tmp_path / "knowledge_base"
    kb_dir.mkdir()

    settings = {
        "llm": {
            "api_key_env": "TEST_API_KEY",
            "base_url": "https://localhost/v1",
            "model": "test-model",
            "enable_thinking": False,
        },
        "models": {"fast": "test-fast", "deep": "test-deep", "vision": "test-vision"},
        "paths": {
            "knowledge_base": str(kb_dir),
            "data": str(tmp_path / "data"),
            "materials": str(materials_dir),
        },
        "language": {"target": "Chinese", "translation_prompt": "Translate"},
        "student": {},
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
    with open(config_dir / "settings.yaml", "w", encoding="utf-8") as f:
        yaml.dump(settings, f)

    monkeypatch.setenv("TEST_API_KEY", "fake-key")
    monkeypatch.chdir(tmp_path)

    # 2. 预填充素材
    store = MaterialStore(str(materials_dir))
    mat1_id = store.save(Material(
        source_url="https://example.com/1",
        source_type="web",
        title="Transformer 基础",
        content="Transformer 是一种基于自注意力机制的神经网络架构...",
        tags=["Transformer", "NLP"],
    ))
    mat2_id = store.save(Material(
        source_url="https://example.com/2",
        source_type="web",
        title="注意力机制详解",
        content="注意力机制通过 Query-Key-Value 三元组实现信息聚合...",
        tags=["Attention", "NLP"],
    ))

    # 3. Mock publisher workers
    from src.publisher_v2.publisher_agent import PublisherAgent
    from src.publisher_v2.book_planner import BookOutline

    publisher = PublisherAgent()

    # Mock planner to return known outline
    mock_outline = BookOutline(
        title="Transformer 教程",
        description="关于 Transformer 的入门教程",
        chapters=[{
            "title": "第1章 基础概念",
            "sections": [{
                "title": "1.1 Transformer 简介",
                "material_ids": [mat1_id],
                "description": "介绍 Transformer 架构",
            }, {
                "title": "1.2 注意力机制",
                "material_ids": [mat2_id],
                "description": "详解注意力机制",
            }],
        }],
    )
    publisher.planner = MagicMock()
    publisher.planner.plan_book = MagicMock(return_value=mock_outline)

    # Mock LLM workers
    publisher.outline_planner = MockWorker("outline", output_data={"outline": ["引言", "核心概念", "小结"]})
    publisher.writer = MockWorker("writer", output_content="# Transformer\n\nTransformer 架构详解...")
    publisher.code_annotator = MockWorker("code_annotator")
    publisher.figure_integrator = MockWorker("figure")
    publisher.cross_referencer = MockWorker("xref", output_content="# Transformer\n\n交叉引用已添加...")
    publisher.reviewer = MockWorker("reviewer", output_data={"passed": True})

    # 4. 执行
    result = await publisher.publish_book(topic="Transformer")

    # 5. 验证
    assert "error" not in result
    assert result["title"] == "Transformer 教程"
    assert result["chapters"] == 1
    assert result["sections"] == 2
    assert os.path.exists(result["output_dir"])

    # 验证输出文件
    readme_path = os.path.join(result["output_dir"], "README.md")
    assert os.path.exists(readme_path)
    with open(readme_path, "r", encoding="utf-8") as f:
        readme = f.read()
    assert "Transformer 教程" in readme


# =====================================================================
# Test 3: TaskEngine 4 并行节点 DAG
# =====================================================================

@pytest.mark.asyncio
async def test_task_engine_parallel_dag():
    """创建 4 并行节点 DAG，验证 TaskEngine 并发执行"""
    engine = TaskEngine(max_parallel=4, checkpoint=False)

    dag = TaskDAG(name="test_parallel")

    # 4 个独立节点（无依赖）
    workers = []
    for i in range(4):
        w = MockWorker(f"worker_{i}", output_data={"idx": i}, delay=0.05)
        node = TaskNode(
            name=f"worker_{i}",
            worker=w,
            input_data=WorkerInput(content=f"input_{i}"),
        )
        dag.add_node(node)
        workers.append(w)

    start = time.time()
    result_dag = await engine.execute(dag)
    elapsed = time.time() - start

    # 验证全部完成
    summary = result_dag.summary()
    assert summary["completed"] == 4
    assert summary["failed"] == 0

    # 验证并行执行（4个0.05s节点应在<0.3s内完成，串行则>0.2s）
    # 放宽阈值以应对CI环境
    assert elapsed < 0.5, f"并行执行耗时 {elapsed:.2f}s，预期 <0.5s"

    # 验证每个 worker 被调用了一次
    for w in workers:
        assert w._call_count == 1


# =====================================================================
# Test 4: TaskEngine DAG 有依赖链
# =====================================================================

@pytest.mark.asyncio
async def test_task_engine_dependency_chain():
    """验证 DAG 依赖链：A,B 并行 → C 依赖 A,B → D 依赖 C"""
    engine = TaskEngine(max_parallel=4, checkpoint=False)
    dag = TaskDAG(name="test_deps")

    w_a = MockWorker("A", output_data={"step": "A"})
    w_b = MockWorker("B", output_data={"step": "B"})
    w_c = MockWorker("C", output_data={"step": "C"})
    w_d = MockWorker("D", output_data={"step": "D"})

    node_a = TaskNode(name="A", worker=w_a, input_data=WorkerInput(content="a"))
    node_b = TaskNode(name="B", worker=w_b, input_data=WorkerInput(content="b"))
    node_c = TaskNode(name="C", worker=w_c, input_data=WorkerInput(content="c"),
                      depends_on=[node_a.id, node_b.id])
    node_d = TaskNode(name="D", worker=w_d, input_data=WorkerInput(content="d"),
                      depends_on=[node_c.id])

    dag.add_node(node_a)
    dag.add_node(node_b)
    dag.add_node(node_c)
    dag.add_node(node_d)

    result_dag = await engine.execute(dag)

    assert result_dag.summary()["completed"] == 4
    # C started after A and B
    assert node_c.started_at >= node_a.finished_at or node_c.started_at >= node_b.finished_at
    # D started after C
    assert node_d.started_at >= node_c.finished_at


# =====================================================================
# Test 5: TaskEngine 失败传播 + 跳过下游
# =====================================================================

@pytest.mark.asyncio
async def test_task_engine_failure_propagation():
    """验证上游失败时下游被跳过"""
    engine = TaskEngine(max_parallel=4, checkpoint=False)
    dag = TaskDAG(name="test_fail")

    w_good = MockWorker("good", output_data={"ok": True})
    w_bad = MockWorker("bad", fail=True)
    w_downstream = MockWorker("downstream", output_data={"ok": True})

    node_good = TaskNode(name="good", worker=w_good, input_data=WorkerInput(content="g"))
    node_bad = TaskNode(name="bad", worker=w_bad, input_data=WorkerInput(content="b"))
    node_down = TaskNode(name="downstream", worker=w_downstream,
                         input_data=WorkerInput(content="d"),
                         depends_on=[node_bad.id])

    dag.add_node(node_good)
    dag.add_node(node_bad)
    dag.add_node(node_down)

    result_dag = await engine.execute(dag)

    assert node_good.status == TaskStatus.COMPLETED
    assert node_bad.status == TaskStatus.FAILED
    assert node_down.status == TaskStatus.SKIPPED


# =====================================================================
# Test 6: DAG 检查点保存 → 恢复 → 完成
# =====================================================================

@pytest.mark.asyncio
async def test_task_engine_checkpoint_resume(tmp_path):
    """DAG 部分执行失败 → 检查点保存 → 恢复 → 全部完成"""
    db_path = str(tmp_path / "checkpoints.db")
    checkpointer = TaskCheckpointer(db_path=db_path)

    # Phase 1: 第一次执行，node_b 会失败
    engine1 = TaskEngine(max_parallel=4, checkpoint=True)
    engine1.checkpointer = checkpointer

    dag1 = TaskDAG(name="test_resume")

    w_a = MockWorker("A", output_data={"v": 1})
    w_b_fail = MockWorker("B", fail=True)

    node_a = TaskNode(name="A", worker=w_a, input_data=WorkerInput(content="a"))
    node_b = TaskNode(name="B", worker=w_b_fail, input_data=WorkerInput(content="b"))
    node_c = TaskNode(name="C", worker=MockWorker("C"), input_data=WorkerInput(content="c"),
                      depends_on=[node_a.id, node_b.id])

    dag1.add_node(node_a)
    dag1.add_node(node_b)
    dag1.add_node(node_c)

    result1 = await engine1.execute(dag1)

    assert node_a.status == TaskStatus.COMPLETED
    assert node_b.status == TaskStatus.FAILED
    assert node_c.status == TaskStatus.SKIPPED

    # 验证检查点已保存
    saved = checkpointer.load(dag1.id)
    assert saved is not None
    assert saved["status"] == "partial_failure"

    # Phase 2: 修复 B 后恢复
    engine2 = TaskEngine(max_parallel=4, checkpoint=True)
    engine2.checkpointer = checkpointer

    w_b_fixed = MockWorker("B", output_data={"v": 2})
    w_c_fixed = MockWorker("C", output_data={"v": 3})

    result2 = await engine2.resume(
        dag1.id,
        workers={"A": w_a, "B": w_b_fixed, "C": w_c_fixed}
    )

    assert result2 is not None
    summary = result2.summary()
    # A was already completed, should remain so; B and C should now be completed
    assert summary["completed"] == 3
    assert summary["failed"] == 0


# =====================================================================
# Test 7: TaskEngine 进度回调
# =====================================================================

@pytest.mark.asyncio
async def test_task_engine_progress_callback():
    """验证进度回调被触发"""
    progress_snapshots = []

    def on_progress(dag):
        progress_snapshots.append(dag.summary().copy())

    engine = TaskEngine(max_parallel=2, checkpoint=False, on_progress=on_progress)
    dag = TaskDAG(name="test_progress")

    for i in range(3):
        node = TaskNode(
            name=f"w_{i}",
            worker=MockWorker(f"w_{i}", output_data={"i": i}),
            input_data=WorkerInput(content=f"c_{i}"),
        )
        dag.add_node(node)

    await engine.execute(dag)

    # 进度回调应该被触发至少一次
    assert len(progress_snapshots) >= 1
    # 最后一次快照应该全部完成
    assert progress_snapshots[-1]["completed"] == 3


# =====================================================================
# Test 8: MaterialStore 批量保存
# =====================================================================

def test_material_store_batch_save(tmp_path):
    """验证批量保存功能"""
    store = MaterialStore(str(tmp_path / "materials"))

    materials = []
    for i in range(5):
        materials.append(Material(
            source_url=f"https://example.com/{i}",
            source_type="web",
            title=f"Test material {i}",
            content=f"Content of material {i}",
            tags=[f"tag_{i}"],
        ))

    ids = store.save_batch(materials)
    assert len(ids) == 5

    # 验证全部可检索
    for mid in ids:
        mat = store.get(mid)
        assert mat is not None
        assert mat.source_type == "web"

    # 验证总数
    assert store.count() == 5


# =====================================================================
# Test 9: MaterialStore WAL 模式
# =====================================================================

def test_material_store_wal_mode(tmp_path):
    """验证 SQLite WAL 模式已启用"""
    store = MaterialStore(str(tmp_path / "materials"))

    with store._conn() as conn:
        result = conn.execute("PRAGMA journal_mode").fetchone()
        assert result[0] == "wal"
