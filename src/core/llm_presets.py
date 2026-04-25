"""
LLM 配置模板
=============
用于在 settings.yaml 和 UI 中快速应用常见供应商模板，避免手工填写
provider / base_url / api_mode / model 组合时出现混搭错误。
"""

from copy import deepcopy
from typing import Dict


PRESETS: Dict[str, dict] = {
    "custom_openai": {
        "label": "自定义 OpenAI 兼容接口",
        "llm": {
            "provider": "openai",
            "api_mode": "auto",
            "api_key_env": "OPENAI_API_KEY",
            "base_url": "https://api.openai.com/v1",
            "model": "gpt-4.1-mini",
            "max_tokens": 4096,
            "vision_max_tokens": 4096,
            "enable_thinking": False,
        },
        "models": {
            "fast": "gpt-4.1-mini",
            "deep": "gpt-5",
            "vision": "gpt-4.1-mini",
        },
    },
    "dashscope_qwen": {
        "label": "阿里云百炼 / DashScope（Qwen 文本优先）",
        "llm": {
            "provider": "openai",
            "api_mode": "chat_completions",
            "api_key_env": "DASHSCOPE_API_KEY",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "model": "qwen3.6-max-preview",
            "max_tokens": 4096,
            "vision_max_tokens": 4096,
            "enable_thinking": True,
        },
        "models": {
            "fast": "qwen3.6-plus",
            "deep": "qwen3.6-max-preview",
            "vision": "qwen3.6-plus",
        },
        "notes": [
            "当前优先优化文本链路：基础对话/深度分析统一走 Qwen 3.6 系列。",
            "deep/主模型默认使用 qwen3.6-max-preview，开启 enable_thinking。",
            "vision 先预留 qwen3.6-plus，后续再接入多模态测试。",
        ],
    },
    "anthropic_claude": {
        "label": "Anthropic Claude",
        "llm": {
            "provider": "anthropic",
            "api_mode": "anthropic_messages",
            "api_key_env": "ANTHROPIC_API_KEY",
            "model": "claude-opus-4-6",
            "max_tokens": 4096,
            "vision_max_tokens": 4096,
            "enable_thinking": True,
            "anthropic": {
                "thinking_budget_tokens": 10000,
                "max_tokens": 8192,
            },
        },
        "models": {
            "fast": "claude-opus-4-6",
            "deep": "claude-opus-4-6",
            "vision": "claude-opus-4-6",
        },
    },
}


def list_presets() -> Dict[str, dict]:
    return deepcopy(PRESETS)


def detect_preset(settings: dict) -> str:
    llm_cfg = settings.get("llm", {}) if settings else {}
    provider = llm_cfg.get("provider", "openai")
    base_url = (llm_cfg.get("base_url") or "").rstrip("/")
    api_key_env = llm_cfg.get("api_key_env", "")

    if provider == "anthropic":
        return "anthropic_claude"
    if base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1" or api_key_env == "DASHSCOPE_API_KEY":
        return "dashscope_qwen"
    return "custom_openai"


def apply_preset_to_settings(settings: dict, preset_name: str) -> dict:
    if preset_name not in PRESETS:
        raise ValueError(f"Unknown LLM preset: {preset_name}")

    updated = deepcopy(settings or {})
    updated.setdefault("llm", {})
    updated.setdefault("models", {})

    existing_api_key = updated["llm"].get("api_key", "")
    existing_anthropic = deepcopy(updated["llm"].get("anthropic", {}))

    preset = deepcopy(PRESETS[preset_name])
    updated["llm"].update(preset["llm"])
    updated["models"].update(preset["models"])

    if preset["llm"].get("provider") == "anthropic":
        merged_anthropic = deepcopy(preset["llm"].get("anthropic", {}))
        merged_anthropic.update(existing_anthropic)
        updated["llm"]["anthropic"] = merged_anthropic
        updated["llm"].pop("base_url", None)
    else:
        updated["llm"].pop("anthropic", None)

    if existing_api_key:
        updated["llm"]["api_key"] = existing_api_key

    return updated
