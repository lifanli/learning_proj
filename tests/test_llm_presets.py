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


def test_apply_xiaomi_mimo_preset_populates_openai_compatible_defaults():
    settings = {
        "llm": {"api_key": "temp-secret"},
        "models": {"fast": "old-fast", "deep": "old-deep", "vision": "old-vision"},
    }

    updated = apply_preset_to_settings(settings, "xiaomi_mimo")

    assert updated["llm"]["provider"] == "openai"
    assert updated["llm"]["base_url"] == "https://token-plan-cn.xiaomimimo.com/v1"
    assert updated["llm"]["api_mode"] == "chat_completions"
    assert updated["llm"]["api_key_env"] == "XIAOMI_MIMO_API_KEY"
    assert updated["llm"]["model"] == "mimo-v2.5-pro"
    assert updated["llm"]["enable_thinking"] is False
    assert updated["llm"]["extra_body"]["chat_template_kwargs"]["enable_thinking"] is False
    assert updated["models"]["fast"] == "mimo-v2.5"
    assert updated["models"]["deep"] == "mimo-v2.5-pro"
    assert updated["models"]["vision"] == "mimo-v2-omni"
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


def test_detect_preset_recognizes_xiaomi_mimo_shape():
    settings = {
        "llm": {
            "provider": "openai",
            "base_url": "https://token-plan-cn.xiaomimimo.com/v1",
            "api_key_env": "XIAOMI_MIMO_API_KEY",
        }
    }

    assert detect_preset(settings) == "xiaomi_mimo"
