from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import yaml

from src.core.progress import reset_progress_reporter, set_progress_reporter
from src.core.worker import WorkerInput
from src.student.curriculum_agent import CurriculumAgent, _CurriculumLLM


def _make_agent():
    agent = object.__new__(CurriculumAgent)
    return agent


def test_parse_curriculum_yaml_accepts_fenced_yaml_with_preface():
    agent = _make_agent()
    result = agent._parse_curriculum_yaml(
        "下面是课程表。\n```yaml\ndomains:\n  - name: 基础\n    topics: []\n```"
    )

    assert result["domains"][0]["name"] == "基础"
    assert result["domains"][0]["priority"] == 99


def test_parse_curriculum_yaml_salvages_domains_after_leading_text():
    agent = _make_agent()
    result = agent._parse_curriculum_yaml(
        "说明文字\n\ndomains:\n  - name: 进阶\n    priority: 2\n    topics: []\n"
    )

    assert len(result["domains"]) == 1
    assert result["domains"][0]["name"] == "进阶"


def test_llm_generate_curriculum_uses_worker_run_wrapper():
    agent = _make_agent()
    worker = MagicMock()
    worker.run.return_value = SimpleNamespace(
        success=True,
        content="domains:\n  - name: 基础\n    topics: []\n",
        error="",
    )
    worker.config = {"llm": {"provider": "openai", "base_url": "https://api.example.com/v1"}}
    worker.get_model.return_value = "gpt-test"
    agent._llm = worker

    result = agent._llm_generate_curriculum("LLM 全栈", "quick")

    assert result["domains"][0]["name"] == "基础"
    worker.run.assert_called_once()


def test_llm_generate_curriculum_raises_readable_error_on_wrapped_failure():
    agent = _make_agent()
    worker = MagicMock()
    worker.run.return_value = SimpleNamespace(
        success=False,
        content="",
        error="502 bad gateway",
    )
    worker.config = {"llm": {"provider": "anthropic", "base_url": "https://gateway.example.com"}}
    worker.get_model.return_value = "claude-test"
    agent._llm = worker

    with pytest.raises(RuntimeError, match="课程表生成的 LLM 调用失败") as exc:
        agent._llm_generate_curriculum("LLM 全栈", "expert")

    message = str(exc.value)
    assert "anthropic" in message
    assert "claude-test" in message
    assert "502 bad gateway" in message


def test_curriculum_llm_falls_back_to_split_generation_after_truncation(mock_settings):
    worker = _CurriculumLLM()
    responses = [
        RuntimeError("LLM response was truncated by output/context limit: length"),
        RuntimeError("LLM response was truncated by output/context limit: length"),
        """```yaml
domains:
  - name: 基础理论
    priority: 1
    description: 打基础
    topic_count: 2
```""",
        """```yaml
topics:
  - name: Transformer 基础
    status: pending
    difficulty: beginner
    description: 理解注意力与编码器解码器
    search_queries:
      - "Transformer tutorial"
      - "Transformer 教程"
      - "attention mechanism explained"
      - "注意力机制 详解"
    known_sources: []
    discovered_sources: []
  - name: Tokenizer 入门
    status: pending
    difficulty: beginner
    description: 理解分词与 token
    search_queries:
      - "tokenizer basics"
      - "tokenizer 基础"
      - "subword tokenization"
      - "子词 分词"
    known_sources: []
    discovered_sources: []
```""",
    ]

    worker.llm_call = MagicMock(side_effect=responses)

    output = worker.execute(WorkerInput(metadata={"goal": "LLM 全栈", "depth": "quick"}))

    assert output.success is True
    assert output.data["mode"] == "split"
    merged = yaml.safe_load(output.content)
    assert merged["domains"][0]["name"] == "基础理论"
    assert len(merged["domains"][0]["topics"]) == 2
    assert worker.llm_call.call_count == 4


def test_curriculum_llm_reports_split_generation_progress(mock_settings):
    worker = _CurriculumLLM()
    worker.llm_call = MagicMock(side_effect=[
        """```yaml
domains:
  - name: 基础理论
    priority: 1
    description: 打基础
    topic_count: 1
```""",
        """```yaml
topics:
  - name: Transformer 基础
    status: pending
    difficulty: beginner
    description: 理解注意力
    search_queries:
      - "Transformer tutorial"
      - "Transformer 教程"
    known_sources: []
    discovered_sources: []
```""",
    ])
    updates = []
    token = set_progress_reporter(lambda progress=None, message=None: updates.append((progress, message)))
    try:
        output = worker.execute(WorkerInput(metadata={"goal": "LLM 全栈", "depth": "expert"}))
    finally:
        reset_progress_reporter(token)

    assert output.success is True
    assert any(message == "课程生成：规划领域骨架" for _, message in updates)
    assert any(message and "课程生成：生成主题" in message for _, message in updates)
    assert any(message == "课程生成：组装课程表 YAML" for _, message in updates)
