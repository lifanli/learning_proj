from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from dotenv import load_dotenv
from lightrag.lightrag import LightRAG, QueryParam
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.utils import EmbeddingFunc

from src.utils.logger import logger

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config" / "settings.yaml"
DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_LLM_MODEL = "qwen3.6-plus"
DEFAULT_EMBEDDING_MODEL = "text-embedding-v2"
DEFAULT_EMBEDDING_DIM = 1536


def _load_project_settings() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, "r", encoding="utf-8") as file:
        loaded = yaml.safe_load(file) or {}
    return loaded if isinstance(loaded, dict) else {}


def _resolve_api_key(llm_cfg: dict[str, Any]) -> str:
    env_name = str(llm_cfg.get("api_key_env") or "DASHSCOPE_API_KEY").strip()
    api_key = (os.getenv(env_name, "") or "").strip() if env_name else ""
    return api_key or str(llm_cfg.get("api_key") or "").strip()


def _resolve_rag_config() -> dict[str, Any]:
    settings = _load_project_settings()
    llm_cfg = settings.get("llm", {}) if isinstance(settings.get("llm", {}), dict) else {}
    models = settings.get("models", {}) if isinstance(settings.get("models", {}), dict) else {}
    embedding_cfg = settings.get("embedding", {}) if isinstance(settings.get("embedding", {}), dict) else {}

    return {
        "api_key": _resolve_api_key(llm_cfg),
        "base_url": llm_cfg.get("base_url") or DEFAULT_BASE_URL,
        "llm_model": models.get("fast") or llm_cfg.get("model") or DEFAULT_LLM_MODEL,
        "embedding_model": embedding_cfg.get("model") or llm_cfg.get("embedding_model") or DEFAULT_EMBEDDING_MODEL,
        "embedding_dim": int(embedding_cfg.get("dimension") or llm_cfg.get("embedding_dim") or DEFAULT_EMBEDDING_DIM),
    }


def _require_api_key(config: dict[str, Any]) -> str:
    api_key = str(config.get("api_key") or "").strip()
    if not api_key:
        raise ValueError("RAG API key is missing. Set the environment variable named by llm.api_key_env.")
    return api_key


async def llm_model_func(prompt, system_prompt=None, history_messages=None, **kwargs) -> str:
    config = _resolve_rag_config()
    return await openai_complete_if_cache(
        config["llm_model"],
        prompt,
        system_prompt=system_prompt,
        history_messages=history_messages or [],
        api_key=_require_api_key(config),
        base_url=config["base_url"],
        **kwargs,
    )


async def embedding_func(texts: list[str]) -> np.ndarray:
    config = _resolve_rag_config()
    return await openai_embed(
        texts,
        model=config["embedding_model"],
        api_key=_require_api_key(config),
        base_url=config["base_url"],
    )


class LightRAGManager:
    def __init__(self, working_dir: str = "./data/rag_store"):
        self.working_dir = working_dir
        if not os.path.exists(working_dir):
            os.makedirs(working_dir)

        config = _resolve_rag_config()
        self.rag = LightRAG(
            working_dir=self.working_dir,
            llm_model_func=llm_model_func,
            embedding_func=EmbeddingFunc(
                embedding_dim=config["embedding_dim"],
                max_token_size=8192,
                func=embedding_func,
            ),
        )

    async def initialize(self):
        """Initialize RAG storages."""
        if hasattr(self.rag, "initialize_storages"):
            await self.rag.initialize_storages()

    async def insert_text(self, text: str):
        """Insert text into the RAG system."""
        try:
            if hasattr(self.rag, "ainsert"):
                await self.rag.ainsert(text)
            else:
                await self.rag.insert(text)
            logger.info("Text inserted into LightRAG")
        except Exception as e:
            logger.error(f"LightRAG insert failed: {e}")

    async def query(self, query_text: str, mode: str = "global") -> str:
        """Query the RAG system. mode: naive, local, global, hybrid."""
        try:
            param = QueryParam(mode=mode)
            if hasattr(self.rag, "aquery"):
                result = await self.rag.aquery(query_text, param=param)
            else:
                result = await self.rag.query(query_text, param=param)

            if not result and mode != "naive":
                logger.info(f"{mode} query returned no result; retrying with naive mode")
                param = QueryParam(mode="naive")
                if hasattr(self.rag, "aquery"):
                    result = await self.rag.aquery(query_text, param=param)
                else:
                    result = await self.rag.query(query_text, param=param)

            return result or ""
        except Exception as e:
            logger.error(f"RAG query failed: {e}")
            if mode != "naive":
                logger.info("Retrying RAG query with naive mode")
                try:
                    param = QueryParam(mode="naive")
                    if hasattr(self.rag, "aquery"):
                        result = await self.rag.aquery(query_text, param=param)
                    else:
                        result = await self.rag.query(query_text, param=param)
                    return result or ""
                except Exception as e2:
                    logger.error(f"RAG naive query also failed: {e2}")
            return ""
