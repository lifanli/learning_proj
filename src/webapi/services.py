from __future__ import annotations

import asyncio
import glob
import json
import os
from pathlib import Path
from typing import Any, Optional

import yaml
from dotenv import dotenv_values, load_dotenv

from src.core.worker import clear_config_cache
from src.core.llm_client import LLMClient
from src.core.material_store import MaterialStore
from src.publisher_v2.publisher_agent import PublisherAgent
from src.student.curriculum_agent import CurriculumAgent
from src.student.student_agent import StudentAgent

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config" / "settings.yaml"
CURRICULUM_PATH = PROJECT_ROOT / "config" / "curriculum.yaml"
LOG_DIR = PROJECT_ROOT / "data" / "logs"
KB_ROOT = PROJECT_ROOT / "knowledge_base"
ENV_PATH = PROJECT_ROOT / ".env"
SENSITIVE_SETTING_KEYS = {
    "api_key",
    "access_key",
    "secret",
    "client_secret",
    "password",
    "token",
    "access_token",
    "refresh_token",
    "private_key",
}


def _is_sensitive_setting_key(key: object) -> bool:
    text = str(key).lower()
    if text.endswith("_env"):
        return False
    return text in SENSITIVE_SETTING_KEYS or text.endswith(("_secret", "_password", "_token", "_key"))


def _sanitize_settings_for_storage(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "" if _is_sensitive_setting_key(key) else _sanitize_settings_for_storage(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitize_settings_for_storage(item) for item in value]
    return value


def _quote_env_value(value: str) -> str:
    if "\n" in value or "\r" in value:
        raise ValueError("secret values cannot contain line breaks")
    if any(ch.isspace() for ch in value) or "#" in value or '"' in value:
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return value


def _upsert_env_value(path: Path, name: str, value: str) -> None:
    if not name or not name.replace("_", "").isalnum() or name[0].isdigit():
        raise ValueError(f"invalid environment variable name: {name!r}")

    path.parent.mkdir(parents=True, exist_ok=True)
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    prefix = f"{name}="
    rendered = f"{name}={_quote_env_value(value)}"
    replaced = False
    updated_lines = []
    for line in lines:
        stripped = line.lstrip()
        if not stripped.startswith("#") and stripped.startswith(prefix):
            updated_lines.append(rendered)
            replaced = True
        else:
            updated_lines.append(line)
    if not replaced:
        updated_lines.append(rendered)
    path.write_text("\n".join(updated_lines).rstrip() + "\n", encoding="utf-8")


def _secret_status(value: str) -> dict:
    value = str(value or "").strip()
    return {
        "present": bool(value),
        "length": len(value),
        "prefix": value[:3] if value else "",
        "suffix": value[-4:] if value else "",
    }


def _sync_llm_api_key_to_env(settings: dict) -> None:
    llm_cfg = settings.get("llm", {}) if isinstance(settings, dict) else {}
    if not isinstance(llm_cfg, dict):
        return

    api_key = str(llm_cfg.get("api_key") or "").strip()
    if not api_key:
        return

    api_key_env = str(llm_cfg.get("api_key_env") or "").strip() or "OPENAI_API_KEY"
    _upsert_env_value(ENV_PATH, api_key_env, api_key)
    os.environ[api_key_env] = api_key


def _get_llm_api_key_env(settings: dict) -> str:
    llm_cfg = settings.get("llm", {}) if isinstance(settings, dict) else {}
    env_name = str(llm_cfg.get("api_key_env") or "").strip()
    if env_name:
        return env_name
    provider = str(llm_cfg.get("provider") or "openai").strip().lower()
    return "ANTHROPIC_API_KEY" if provider == "anthropic" else "OPENAI_API_KEY"


def _redact_settings(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "***" if _is_sensitive_setting_key(key) and item not in (None, "") else _redact_settings(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_settings(item) for item in value]
    return value


def _dump_settings(settings: dict) -> str:
    if not settings:
        return ""
    return yaml.safe_dump(settings, allow_unicode=True, default_flow_style=False, sort_keys=False)


def _load_settings() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_settings_text() -> str:
    if not CONFIG_PATH.exists():
        return ""
    return _dump_settings(_sanitize_settings_for_storage(_load_settings()))


def save_settings_text(content: str) -> dict:
    parsed = yaml.safe_load(content) or {}
    if not isinstance(parsed, dict):
        raise ValueError("settings content must be a YAML mapping")
    _sync_llm_api_key_to_env(parsed)
    sanitized = _sanitize_settings_for_storage(parsed)
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(_dump_settings(sanitized), encoding="utf-8")
    clear_config_cache()
    return sanitized


def get_llm_runtime_status() -> dict:
    settings = _load_settings()
    llm_cfg = settings.get("llm", {}) if isinstance(settings, dict) else {}
    api_key_env = _get_llm_api_key_env(settings)
    load_dotenv(dotenv_path=ENV_PATH, override=True)
    env_file_values = dotenv_values(ENV_PATH) if ENV_PATH.exists() else {}
    return {
        "provider": llm_cfg.get("provider", "openai"),
        "api_mode": llm_cfg.get("api_mode", "auto"),
        "base_url": llm_cfg.get("base_url", ""),
        "model": llm_cfg.get("model", ""),
        "fast_model": settings.get("models", {}).get("fast", ""),
        "deep_model": settings.get("models", {}).get("deep", ""),
        "api_key_env": api_key_env,
        "env_file": str(ENV_PATH),
        "env_file_exists": ENV_PATH.exists(),
        "env_file_key": _secret_status(env_file_values.get(api_key_env, "")),
        "process_key": _secret_status(os.getenv(api_key_env, "")),
    }


def save_llm_api_key(api_key: str, api_key_env: Optional[str] = None) -> dict:
    cleaned_key = str(api_key or "").strip()
    if not cleaned_key:
        raise ValueError("API Key 不能为空")

    settings = _load_settings()
    llm_cfg = settings.setdefault("llm", {})
    env_name = str(api_key_env or llm_cfg.get("api_key_env") or "").strip() or _get_llm_api_key_env(settings)
    llm_cfg["api_key_env"] = env_name
    llm_cfg["api_key"] = ""

    _upsert_env_value(ENV_PATH, env_name, cleaned_key)
    os.environ[env_name] = cleaned_key
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(_dump_settings(_sanitize_settings_for_storage(settings)), encoding="utf-8")
    clear_config_cache()
    return get_llm_runtime_status()


def check_llm_connection() -> dict:
    settings = _load_settings()
    llm_cfg = settings.get("llm", {}) if isinstance(settings, dict) else {}
    model = settings.get("models", {}).get("fast") or llm_cfg.get("model")
    if not model:
        return {"ok": False, "error": "未配置可用模型"}
    try:
        client = LLMClient(settings)
        reply = client.chat_completion(
            messages=[{"role": "user", "content": "只回复 OK"}],
            model=model,
            stream=False,
            enable_thinking=False,
            temperature=0,
            timeout=30,
            max_tokens=8,
        )
        return {"ok": True, "model": model, "reply": str(reply).strip()[:40], "status": get_llm_runtime_status()}
    except Exception as exc:
        return {
            "ok": False,
            "model": model,
            "error": str(exc),
            "status": get_llm_runtime_status(),
        }


def get_material_store() -> MaterialStore:
    settings = _load_settings()
    materials_path = settings.get("paths", {}).get("materials", "data/materials")
    return MaterialStore(str((PROJECT_ROOT / materials_path).resolve()) if not os.path.isabs(materials_path) else materials_path)


def serialize_material(material, include_content: bool = False) -> dict:
    payload = material.to_dict()
    if not include_content:
        payload["content"] = ""
    return payload


def get_dashboard_summary() -> dict:
    store = get_material_store()
    curriculum = get_curriculum()
    progress = CurriculumAgent().get_progress() if curriculum else {"total": 0, "done": 0, "studying": 0, "pending": 0}
    latest_logs = list_log_files()[:5]
    return {
        "materials_total": store.count(),
        "materials_by_type": {
            kind: store.count(kind)
            for kind in ["course", "course_page", "github", "arxiv", "wechat", "web"]
        },
        "curriculum": {
            "exists": bool(curriculum),
            "status": curriculum.get("status") if curriculum else None,
            "goal": curriculum.get("goal") if curriculum else None,
            "progress": progress,
        },
        "log_files": latest_logs,
    }


def get_curriculum() -> Optional[dict]:
    agent = CurriculumAgent()
    curriculum = agent.load()
    if not curriculum:
        return None
    return curriculum


def generate_curriculum(goal: str, depth: str) -> dict:
    return CurriculumAgent().generate(goal=goal, depth=depth)


def approve_curriculum() -> dict:
    agent = CurriculumAgent()
    agent.approve()
    return agent.load() or {}


def run_auto_study() -> dict:
    return asyncio.run(StudentAgent().study_curriculum())


def run_manual_study(mode: str, value: str, max_pages: int = 50) -> dict:
    agent = StudentAgent()
    if mode == "study-topic":
        return asyncio.run(agent.study_topic(value))
    if mode == "study-course":
        return asyncio.run(agent.study_course(value, max_pages=max_pages))
    if mode == "study-github":
        return asyncio.run(agent.study_github(value))
    if mode == "study-arxiv":
        return asyncio.run(agent.study_arxiv(value))
    if mode == "study-wechat":
        return asyncio.run(agent.study_wechat(value))
    raise ValueError(f"Unknown study mode: {mode}")


def run_publish(topic: str, parent_id: Optional[str] = None, tags: Optional[list[str]] = None) -> dict:
    return asyncio.run(PublisherAgent().publish_book(topic=topic, parent_id=parent_id, tags=tags))


def list_materials(source_type: Optional[str] = None, keyword: Optional[str] = None, limit: int = 100) -> list[dict]:
    store = get_material_store()
    return [serialize_material(item) for item in store.query(source_type=source_type, keyword=keyword, limit=limit)]


def get_material(material_id: str) -> Optional[dict]:
    material = get_material_store().get(material_id)
    if not material:
        return None
    return serialize_material(material, include_content=True)


def list_log_files() -> list[str]:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return [os.path.basename(path) for path in sorted(glob.glob(str(LOG_DIR / "*.log")), reverse=True)]


def _resolve_under(root: Path, relative_path: str) -> Path:
    root_resolved = root.resolve()
    target = (root_resolved / relative_path).resolve()
    try:
        target.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError("Invalid path") from exc
    return target


def read_log_file(name: str, limit: int = 300) -> dict:
    try:
        path = _resolve_under(LOG_DIR, name)
    except ValueError as exc:
        raise FileNotFoundError(name) from exc
    if path.parent != LOG_DIR.resolve():
        raise FileNotFoundError(name)
    if not path.is_file():
        raise FileNotFoundError(name)
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    return {"name": name, "lines": lines[-limit:], "total_lines": len(lines)}


def _walk_markdown(root: Path) -> list[dict]:
    items = []
    if not root.exists():
        return items
    for child in sorted(root.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
        node = {"name": child.name, "path": str(child.relative_to(KB_ROOT)), "type": "directory" if child.is_dir() else "file"}
        if child.is_dir():
            node["children"] = _walk_markdown(child)
        items.append(node)
    return items


def get_knowledge_tree() -> list[dict]:
    return _walk_markdown(KB_ROOT)


def read_knowledge_file(relative_path: str) -> dict:
    try:
        target = _resolve_under(KB_ROOT, relative_path)
    except ValueError:
        raise ValueError("Invalid knowledge base path")
    if not target.exists() or not target.is_file():
        raise FileNotFoundError(relative_path)
    return {"path": relative_path, "content": target.read_text(encoding="utf-8", errors="ignore")}


def get_system_state() -> dict:
    settings = _load_settings()
    curriculum = get_curriculum()
    return {
        "project_root": str(PROJECT_ROOT),
        "settings": _redact_settings(settings),
        "curriculum_exists": bool(curriculum),
        "curriculum_status": curriculum.get("status") if curriculum else None,
        "logs": list_log_files()[:10],
    }
