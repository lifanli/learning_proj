"""课程规划链路的补充回归测试"""

from unittest.mock import patch

import pytest

from src.core.llm_client import LLMClient
from src.student.curriculum_agent import CurriculumAgent


class TestLlmClientBaseUrlNormalization:
    def test_normalize_openai_base_url_appends_v1_for_bare_host(self):
        assert LLMClient._normalize_openai_base_url("https://aicoding.2233.ai") == "https://aicoding.2233.ai/v1"

    def test_normalize_openai_base_url_keeps_existing_path(self):
        assert LLMClient._normalize_openai_base_url("https://api.example.com/v1") == "https://api.example.com/v1"
        assert LLMClient._normalize_openai_base_url("https://api.example.com/openai/v1") == "https://api.example.com/openai/v1"


class TestLlmClientApiKeyResolution:
    def test_falls_back_to_config_api_key_when_env_is_missing(self, monkeypatch):
        monkeypatch.delenv("MISSING_API_KEY", raising=False)

        client = LLMClient({
            "llm": {
                "provider": "openai",
                "api_key_env": "MISSING_API_KEY",
                "api_key": " config-key ",
                "base_url": "https://example.com/v1",
            }
        })

        assert client.client.api_key == "config-key"

    def test_blank_env_does_not_shadow_config_api_key(self, monkeypatch):
        monkeypatch.setenv("BLANK_API_KEY", "   ")

        client = LLMClient({
            "llm": {
                "provider": "openai",
                "api_key_env": "BLANK_API_KEY",
                "api_key": "fallback-key",
                "base_url": "https://example.com/v1",
            }
        })

        assert client.client.api_key == "fallback-key"


class TestCurriculumAgentFailureHandling:
    def test_generate_raises_when_llm_returns_empty_domains(self):
        agent = object.__new__(CurriculumAgent)
        agent.registry = []
        agent._match_registry_sources = lambda curriculum: None
        agent._llm_generate_curriculum = lambda goal, depth: {"domains": []}

        with pytest.raises(RuntimeError, match="课程表生成失败"):
            agent.generate("LLM全栈工程师", "expert")

    def test_generate_does_not_save_when_llm_call_fails(self):
        agent = object.__new__(CurriculumAgent)
        agent.registry = []
        agent._match_registry_sources = lambda curriculum: None
        agent._llm_generate_curriculum = lambda goal, depth: (_ for _ in ()).throw(RuntimeError("404 page not found"))
        agent.save = lambda curriculum, path=None: (_ for _ in ()).throw(AssertionError("save should not be called"))

        with pytest.raises(RuntimeError, match="404 page not found"):
            agent.generate("LLM全栈工程师", "expert")
