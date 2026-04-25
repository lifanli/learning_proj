from types import SimpleNamespace

from src.core.llm_client import LLMClient


class _FakeResponsesAPI:
    def __init__(self, results):
        self.results = results
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.results[len(self.calls) - 1]


def _make_response(output_text=None, status="completed", output=None):
    return SimpleNamespace(output_text=output_text, status=status, output=output or [])


def test_responses_chat_retries_with_flattened_prompt_when_structured_output_is_empty():
    client = object.__new__(LLMClient)
    client._config = {"llm": {}}
    client._provider = "openai"
    fake_api = _FakeResponsesAPI([
        _make_response(output_text="", status="completed", output=[]),
        _make_response(output_text="domains:\n  - name: 基础\n", status="completed", output=[]),
    ])
    client._client = SimpleNamespace(responses=fake_api)

    result = client._openai_responses_chat(
        messages=[
            {"role": "system", "content": "你是课程设计专家"},
            {"role": "user", "content": "请输出 YAML"},
        ],
        model="gpt-5.4",
        max_tokens=1000,
        timeout=30,
    )

    assert "domains:" in result
    assert isinstance(fake_api.calls[0]["input"], list)
    assert isinstance(fake_api.calls[1]["input"], str)
    assert "[system]" in fake_api.calls[1]["input"]
