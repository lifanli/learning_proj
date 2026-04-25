import hashlib
import json
import os
import re
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Callable

from src.utils.logger import logger


# Pipeline step identifiers
STEP_NAMES = [
    "rag_insert",
    "translate_topic",
    "plan_structure",
    "rag_query",
    "translate_rag",
    "compose_article",
    "fact_check",
    "write_file",
]

# Chinese display names for UI
STEP_DISPLAY_NAMES = [
    "存入RAG知识图谱",
    "翻译主题和摘要",
    "目录分类规划",
    "RAG综合查询",
    "翻译综合内容",
    "生成文档",
    "事实核查",
    "写入文件",
]


@dataclass
class PipelineState:
    """Pipeline state, checkpointed to SQLite after each step."""
    # Input
    content: str = ""
    source: str = ""
    topic: str = ""

    # Step outputs
    translated_topic: str = ""
    translated_summary: str = ""
    target_dir: str = ""
    dir_path: str = ""
    rag_content: str = ""
    translated_rag: str = ""
    final_content: str = ""
    output_path: str = ""

    # Pipeline metadata
    thread_id: str = ""
    current_step: int = 0       # Next step to execute (0 = not started, 8 = done)
    status: str = "pending"     # pending | running | paused | completed | error
    error_message: str = ""
    created_at: str = ""
    updated_at: str = ""


class PipelineCheckpointer:
    """SQLite-based checkpoint storage for pipeline state."""

    def __init__(self, db_path: str = "data/pipeline_checkpoints.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    thread_id TEXT PRIMARY KEY,
                    state_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.commit()

    def save(self, state: PipelineState):
        state.updated_at = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO checkpoints (thread_id, state_json, updated_at) VALUES (?, ?, ?)",
                (state.thread_id, json.dumps(asdict(state), ensure_ascii=False), state.updated_at)
            )
            conn.commit()

    def load(self, thread_id: str) -> Optional[PipelineState]:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT state_json FROM checkpoints WHERE thread_id = ?",
                (thread_id,)
            ).fetchone()
        if row:
            data = json.loads(row[0])
            return PipelineState(**data)
        return None

    def delete(self, thread_id: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
            conn.commit()

    def list_all(self) -> list:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT state_json FROM checkpoints ORDER BY updated_at DESC"
            ).fetchall()
        results = []
        for (state_json,) in rows:
            data = json.loads(state_json)
            results.append(PipelineState(**data))
        return results


class KnowledgePipeline:
    """
    8-step knowledge processing pipeline with SQLite checkpoint-based pause/resume.

    Steps:
    1. RAG Insert      - Store raw content in knowledge graph
    2. Translate Topic  - Translate topic and content summary to Chinese
    3. Plan Structure   - Determine target directory via LLM
    4. RAG Query        - Comprehensive query for related knowledge
    5. Translate RAG    - Translate RAG output to Chinese
    6. Compose Article  - Generate final Markdown article via LLM
    7. Fact Check       - Verify factual accuracy
    8. Write File       - Write to knowledge base filesystem

    Pause/Resume:
    - Set pause via set_pause() (writes a flag file)
    - Pipeline checks the flag between steps
    - State is checkpointed after every step
    - Resume by calling process() again with the same source URL
    """

    PAUSE_FLAG = "data/pipeline_pause.flag"

    def __init__(self, editor, db_path: str = "data/pipeline_checkpoints.db"):
        """
        Args:
            editor: An initialized EditorAgent instance.
            db_path: Path to SQLite checkpoint database.
        """
        self.editor = editor
        self.checkpointer = PipelineCheckpointer(db_path)

    @staticmethod
    def make_thread_id(url: str) -> str:
        """Generate deterministic thread_id from URL."""
        return hashlib.md5(url.encode()).hexdigest()[:12]

    def is_paused(self) -> bool:
        """Check if the global pause flag is set."""
        return os.path.exists(self.PAUSE_FLAG)

    def set_pause(self):
        """Set the global pause flag. Pipeline will pause at the next step boundary."""
        os.makedirs(os.path.dirname(self.PAUSE_FLAG), exist_ok=True)
        with open(self.PAUSE_FLAG, "w") as f:
            f.write(datetime.now().isoformat())
        logger.info("Pipeline pause flag set")

    def clear_pause(self):
        """Clear the global pause flag."""
        if os.path.exists(self.PAUSE_FLAG):
            os.remove(self.PAUSE_FLAG)
        logger.info("Pipeline pause flag cleared")

    def get_status(self, thread_id: str) -> Optional[PipelineState]:
        """Get the current state of a pipeline by thread_id."""
        return self.checkpointer.load(thread_id)

    def list_pipelines(self) -> list:
        """List all pipeline checkpoints."""
        return self.checkpointer.list_all()

    def delete_pipeline(self, thread_id: str):
        """Delete a pipeline checkpoint."""
        self.checkpointer.delete(thread_id)

    async def process(self, content: str, source: str, topic: str,
                      on_step_start: Callable = None,
                      on_step_done: Callable = None) -> PipelineState:
        """
        Run the full pipeline. Automatically resumes from checkpoint if one exists.

        Args:
            content: Raw content to process.
            source: Source URL.
            topic: Content topic/title.
            on_step_start: Callback(step_index, step_name) called before each step.
            on_step_done: Callback(step_index, step_name, state) called after each step.

        Returns:
            Final PipelineState with status indicating outcome.
        """
        thread_id = self.make_thread_id(source)

        # Check for existing checkpoint (resume scenario)
        state = self.checkpointer.load(thread_id)
        if state and state.status in ("paused", "running", "error"):
            logger.info(
                f"恢复流水线 {thread_id} 从步骤 {state.current_step} "
                f"({STEP_NAMES[state.current_step] if state.current_step < len(STEP_NAMES) else 'done'})"
            )
        else:
            # Create new pipeline state
            state = PipelineState(
                content=content,
                source=source,
                topic=topic,
                thread_id=thread_id,
                current_step=0,
                status="running",
                created_at=datetime.now().isoformat()
            )

        state.status = "running"
        state.error_message = ""
        self.checkpointer.save(state)

        steps = [
            self._step_rag_insert,
            self._step_translate_topic,
            self._step_plan_structure,
            self._step_rag_query,
            self._step_translate_rag,
            self._step_compose_article,
            self._step_fact_check,
            self._step_write_file,
        ]

        try:
            for i in range(state.current_step, len(steps)):
                # Check pause flag between steps
                if self.is_paused():
                    state.status = "paused"
                    state.current_step = i
                    self.checkpointer.save(state)
                    logger.info(f"流水线 {thread_id} 已暂停于步骤 {i} ({STEP_NAMES[i]})")
                    return state

                step_name = STEP_NAMES[i]
                if on_step_start:
                    on_step_start(i, step_name)

                logger.info(f"流水线 {thread_id} 执行步骤 {i + 1}/8: {STEP_DISPLAY_NAMES[i]}")
                state = await steps[i](state)
                state.current_step = i + 1
                self.checkpointer.save(state)

                if on_step_done:
                    on_step_done(i, step_name, state)

            state.status = "completed"
            self.checkpointer.save(state)
            logger.info(f"流水线 {thread_id} 完成: {state.output_path}")

        except Exception as e:
            state.status = "error"
            state.error_message = str(e)
            self.checkpointer.save(state)
            logger.error(f"流水线 {thread_id} 在步骤 {state.current_step} 出错: {e}")

        return state

    # ===== Pipeline Steps =====

    async def _step_rag_insert(self, state: PipelineState) -> PipelineState:
        """Step 1: Insert content into RAG knowledge graph."""
        enriched_text = f"来源: {state.source}\n主题: {state.topic}\n\n{state.content}"
        await self.editor.rag.insert_text(enriched_text)
        return state

    async def _step_translate_topic(self, state: PipelineState) -> PipelineState:
        """Step 2: Translate topic and content summary."""
        state.translated_topic = self.editor.translator.translate(state.topic)
        content_summary = state.content[:800]
        state.translated_summary = self.editor.translator.translate(content_summary)
        return state

    async def _step_plan_structure(self, state: PipelineState) -> PipelineState:
        """Step 3: Plan directory structure via LLM."""
        state.target_dir = self.editor.planner.plan(state.translated_topic, state.translated_summary)
        state.dir_path = os.path.join(self.editor.kb_root, state.target_dir)
        os.makedirs(state.dir_path, exist_ok=True)
        logger.info(f"内容归入分类: {state.target_dir}")
        return state

    async def _step_rag_query(self, state: PipelineState) -> PipelineState:
        """Step 4: RAG comprehensive query for related knowledge."""
        query = f"请综合介绍关于「{state.translated_topic}」的技术细节，包括核心概念、关键关系和最新进展。"
        state.rag_content = await self.editor.rag.query(query, mode="hybrid")
        state.rag_content = state.rag_content or ""
        return state

    async def _step_translate_rag(self, state: PipelineState) -> PipelineState:
        """Step 5: Translate RAG output to Chinese."""
        state.translated_rag = self.editor.translator.translate(state.rag_content) if state.rag_content else ""
        return state

    async def _step_compose_article(self, state: PipelineState) -> PipelineState:
        """Step 6: Compose final Markdown article via LLM."""
        state.final_content = self.editor._compose_article(
            state.translated_topic, state.translated_rag, state.source, state.translated_summary
        )
        return state

    async def _step_fact_check(self, state: PipelineState) -> PipelineState:
        """Step 7: Fact check the article."""
        check_result = self.editor.fact_checker.check(
            state.final_content, state.source, state.rag_content or ""
        )
        if not check_result["passed"]:
            logger.warning(f"事实核查发现问题: {check_result['issues']}")
            state.final_content = check_result["corrected_content"]
        else:
            logger.info("事实核查通过")
        return state

    async def _step_write_file(self, state: PipelineState) -> PipelineState:
        """Step 8: Write final content to Markdown file."""
        safe_topic = state.translated_topic.replace("\n", " ").replace("\r", " ")
        safe_topic = re.sub(r'^[\s\-#=]+', '', safe_topic)
        safe_topic = re.sub(r'[\s\-#=]+$', '', safe_topic)
        for ch in r'\/:*?"<>|':
            safe_topic = safe_topic.replace(ch, "_")
        safe_topic = re.sub(r'[_\s]+', ' ', safe_topic).strip()[:50]
        if not safe_topic:
            safe_topic = "未命名文章"

        filename = f"{safe_topic}.md"
        file_path = os.path.join(state.dir_path, filename)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(state.final_content)

        state.output_path = file_path
        logger.info(f"知识已写入: {file_path}")
        return state
