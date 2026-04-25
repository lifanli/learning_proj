"""
任务 DAG 引擎
=============
将大任务分解为多个Worker小任务，支持DAG依赖、并行执行、checkpoint。

核心概念：
- TaskNode: DAG中的一个节点，对应一个Worker执行
- TaskDAG: 节点集合 + 依赖关系
- TaskEngine: 调度引擎，按拓扑序执行，支持并行
"""

import asyncio
import json
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from src.core.worker import BaseWorker, WorkerInput, WorkerOutput
from src.utils.logger import logger


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TaskNode:
    """DAG中的一个任务节点"""
    id: str = ""
    name: str = ""                          # 可读名称
    worker: Optional[BaseWorker] = None
    input_data: Optional[WorkerInput] = None
    output: Optional[WorkerOutput] = None
    status: TaskStatus = TaskStatus.PENDING
    depends_on: List[str] = field(default_factory=list)  # 依赖的node id列表
    error: str = ""
    started_at: float = 0.0
    finished_at: float = 0.0

    # 输入转换函数：从上游节点输出构建本节点输入
    input_builder: Optional[Callable] = None

    def __post_init__(self):
        if not self.id:
            self.id = uuid.uuid4().hex[:8]


@dataclass
class TaskDAG:
    """任务有向无环图"""
    id: str = ""
    name: str = ""
    nodes: Dict[str, TaskNode] = field(default_factory=dict)
    created_at: float = 0.0

    def __post_init__(self):
        if not self.id:
            self.id = uuid.uuid4().hex[:12]
        if not self.created_at:
            self.created_at = time.time()

    def add_node(self, node: TaskNode) -> str:
        """添加节点，返回node_id"""
        self.nodes[node.id] = node
        return node.id

    def add_dependency(self, node_id: str, depends_on_id: str):
        """添加依赖关系"""
        if node_id in self.nodes and depends_on_id in self.nodes:
            if depends_on_id not in self.nodes[node_id].depends_on:
                self.nodes[node_id].depends_on.append(depends_on_id)

    def get_ready_nodes(self) -> List[TaskNode]:
        """获取所有依赖已完成、自身待执行的节点"""
        ready = []
        for node in self.nodes.values():
            if node.status != TaskStatus.PENDING:
                continue
            deps_met = all(
                self.nodes[dep_id].status == TaskStatus.COMPLETED
                for dep_id in node.depends_on
                if dep_id in self.nodes
            )
            if deps_met:
                ready.append(node)
        return ready

    def is_complete(self) -> bool:
        """所有节点已完成或失败"""
        return all(
            n.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.SKIPPED)
            for n in self.nodes.values()
        )

    def get_failed_nodes(self) -> List[TaskNode]:
        return [n for n in self.nodes.values() if n.status == TaskStatus.FAILED]

    def summary(self) -> Dict[str, int]:
        """返回各状态的节点计数"""
        counts = {s.value: 0 for s in TaskStatus}
        for node in self.nodes.values():
            counts[node.status.value] += 1
        return counts


class TaskCheckpointer:
    """DAG执行检查点持久化"""

    def __init__(self, db_path: str = "data/task_checkpoints.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dag_checkpoints (
                    dag_id TEXT PRIMARY KEY,
                    dag_name TEXT,
                    nodes_json TEXT,
                    status TEXT,
                    created_at REAL,
                    updated_at REAL
                )
            """)

    def save(self, dag: TaskDAG):
        """保存DAG状态"""
        nodes_data = {}
        for nid, node in dag.nodes.items():
            nodes_data[nid] = {
                "name": node.name,
                "status": node.status.value,
                "depends_on": node.depends_on,
                "error": node.error,
                "started_at": node.started_at,
                "finished_at": node.finished_at,
            }

        status = "completed" if dag.is_complete() else "running"
        if dag.get_failed_nodes():
            status = "partial_failure"

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO dag_checkpoints
                (dag_id, dag_name, nodes_json, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                dag.id, dag.name,
                json.dumps(nodes_data, ensure_ascii=False),
                status, dag.created_at, time.time()
            ))

    def load(self, dag_id: str) -> Optional[Dict]:
        """加载DAG检查点"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM dag_checkpoints WHERE dag_id = ?", (dag_id,)
            ).fetchone()
            if row:
                return dict(row)
        return None


class TaskEngine:
    """
    任务DAG引擎 - 按拓扑序执行Worker节点。

    支持：
    - 并行执行无依赖的节点
    - 检查点保存/恢复
    - 失败节点跳过下游
    - 进度回调
    """

    def __init__(self, max_parallel: int = 5, checkpoint: bool = True,
                 on_progress: Optional[Callable[[TaskDAG], None]] = None):
        self.max_parallel = max_parallel
        self.checkpoint = checkpoint
        self.checkpointer = TaskCheckpointer() if checkpoint else None
        self.on_progress = on_progress

    async def execute(self, dag: TaskDAG) -> TaskDAG:
        """执行整个DAG"""
        logger.info(f"[TaskEngine] 开始执行DAG: {dag.name} ({len(dag.nodes)}个节点)")

        while not dag.is_complete():
            ready = dag.get_ready_nodes()
            if not ready:
                # 检查是否有节点因上游失败而无法执行
                self._skip_blocked_nodes(dag)
                if not dag.get_ready_nodes():
                    break

            # 并行执行就绪节点（受max_parallel限制）
            batch = ready[:self.max_parallel]
            tasks = [self._execute_node(dag, node) for node in batch]
            await asyncio.gather(*tasks)

            # 保存检查点
            if self.checkpointer:
                self.checkpointer.save(dag)

            # 触发进度回调
            if self.on_progress:
                try:
                    self.on_progress(dag)
                except Exception as e:
                    logger.warning(f"[TaskEngine] 进度回调异常: {e}")

        summary = dag.summary()
        logger.info(
            f"[TaskEngine] DAG执行完成: {dag.name} | "
            f"completed={summary['completed']}, failed={summary['failed']}, "
            f"skipped={summary['skipped']}"
        )
        return dag

    async def resume(self, dag_id: str, workers: Dict[str, BaseWorker]) -> Optional[TaskDAG]:
        """
        从检查点恢复并继续执行 DAG。

        Args:
            dag_id: 之前执行的 DAG ID
            workers: {node_name: worker_instance} 映射，用于重建节点的 worker

        Returns:
            恢复后完成的 TaskDAG，或 None（如果找不到检查点）
        """
        if not self.checkpointer:
            logger.error("[TaskEngine] 检查点功能未启用，无法恢复")
            return None

        checkpoint = self.checkpointer.load(dag_id)
        if not checkpoint:
            logger.error(f"[TaskEngine] 未找到DAG检查点: {dag_id}")
            return None

        # 重建 DAG
        dag = TaskDAG(
            id=checkpoint["dag_id"],
            name=checkpoint["dag_name"],
            created_at=checkpoint["created_at"],
        )

        nodes_data = json.loads(checkpoint["nodes_json"])
        for nid, ndata in nodes_data.items():
            status = TaskStatus(ndata["status"])
            worker = workers.get(ndata["name"])

            node = TaskNode(
                id=nid,
                name=ndata["name"],
                worker=worker,
                status=status,
                depends_on=ndata.get("depends_on", []),
                error=ndata.get("error", ""),
                started_at=ndata.get("started_at", 0.0),
                finished_at=ndata.get("finished_at", 0.0),
            )

            # 已完成的节点保持原状；失败/运行中的节点重置为 pending 以重试
            if status in (TaskStatus.FAILED, TaskStatus.RUNNING):
                node.status = TaskStatus.PENDING
                node.error = ""
            # SKIPPED 的节点也重置，让其依赖链重新评估
            elif status == TaskStatus.SKIPPED:
                node.status = TaskStatus.PENDING
                node.error = ""

            dag.add_node(node)

        logger.info(
            f"[TaskEngine] 从检查点恢复DAG: {dag.name} | "
            f"{sum(1 for n in dag.nodes.values() if n.status == TaskStatus.PENDING)}个节点待重试"
        )

        # 继续执行
        return await self.execute(dag)

    async def _execute_node(self, dag: TaskDAG, node: TaskNode):
        """执行单个节点"""
        node.status = TaskStatus.RUNNING
        node.started_at = time.time()

        try:
            # 如果有input_builder，从上游构建输入
            if node.input_builder:
                upstream_outputs = {
                    dep_id: dag.nodes[dep_id].output
                    for dep_id in node.depends_on
                    if dep_id in dag.nodes and dag.nodes[dep_id].output
                }
                node.input_data = node.input_builder(upstream_outputs, node.input_data)

            if node.worker and node.input_data:
                # 在线程池中执行同步Worker，支持超时控制
                loop = asyncio.get_event_loop()
                coro = loop.run_in_executor(
                    None, node.worker.run, node.input_data
                )

                # 使用 worker spec 的 timeout（如有）
                timeout = node.worker.spec.timeout if node.worker.spec.timeout else None
                if timeout:
                    node.output = await asyncio.wait_for(coro, timeout=timeout)
                else:
                    node.output = await coro

                if node.output.success:
                    node.status = TaskStatus.COMPLETED
                else:
                    node.status = TaskStatus.FAILED
                    node.error = node.output.error
            else:
                # 无Worker的占位节点直接完成
                node.status = TaskStatus.COMPLETED
                node.output = WorkerOutput(success=True)

        except asyncio.TimeoutError:
            node.status = TaskStatus.FAILED
            node.error = f"节点 {node.name} 执行超时 ({node.worker.spec.timeout}s)"
            logger.error(f"[TaskEngine] {node.error}")

        except Exception as e:
            node.status = TaskStatus.FAILED
            node.error = str(e)
            logger.error(f"[TaskEngine] 节点执行失败 {node.name}: {e}")

        node.finished_at = time.time()

    def _skip_blocked_nodes(self, dag: TaskDAG):
        """跳过因上游失败而无法执行的节点"""
        failed_ids: Set[str] = {n.id for n in dag.get_failed_nodes()}

        changed = True
        while changed:
            changed = False
            for node in dag.nodes.values():
                if node.status != TaskStatus.PENDING:
                    continue
                # 如果任何依赖失败或被跳过
                for dep_id in node.depends_on:
                    dep = dag.nodes.get(dep_id)
                    if dep and dep.status in (TaskStatus.FAILED, TaskStatus.SKIPPED):
                        node.status = TaskStatus.SKIPPED
                        node.error = f"上游节点 {dep_id} 失败/跳过"
                        logger.warning(f"[TaskEngine] 跳过节点 {node.name}: {node.error}")
                        changed = True
                        break
