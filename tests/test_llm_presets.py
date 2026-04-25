from src.core.llm_presets import apply_preset_to_settings, detect_preset


def test_apply_dashscope_qwen_preset_populates_text_first_defaults():
    settings = {
        "llm": {"api_key": "temp-secret"},
        "models": {"fast": "old-fast", "deep": "old-deep", "vision": "old-vision"},
    }

    updated = apply_preset_to_settings(settings, "dashscope_qwen")

    assert updated["llm"]["provider"] == "openai"
    assert updated["llm"]["base_url"] == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert updated["llm"]["api_mode"] == "chat_completions"
    assert updated["llm"]["api_key_env"] == "DASHSCOPE_API_KEY"
    assert updated["llm"]["model"] == "qwen3.6-max-preview"
    assert updated["llm"]["enable_thinking"] is True
    assert updated["models"]["deep"] == "qwen3.6-max-preview"
    assert updated["models"]["vision"] == "qwen3.6-plus"
    assert updated["llm"]["api_key"] == "temp-secret"


def test_apply_anthropic_preset_removes_openai_only_fields():
    settings = {
        "llm": {
            "provider": "openai",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "api_mode": "chat_completions",
        },
        "models": {},
    }

    updated = apply_preset_to_settings(settings, "anthropic_claude")

    assert updated["llm"]["provider"] == "anthropic"
    assert updated["llm"]["api_mode"] == "anthropic_messages"
    assert "base_url" not in updated["llm"]
    assert updated["llm"]["api_key_env"] == "ANTHROPIC_API_KEY"


def test_detect_preset_recognizes_dashscope_qwen_shape():
    settings = {
        "llm": {
            "provider": "openai",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "api_key_env": "DASHSCOPE_API_KEY",
        }
    }

    assert detect_preset(settings) == "dashscope_qwen"
