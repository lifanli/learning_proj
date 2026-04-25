"""
Worker 基类
===========
所有 Student/Publisher Worker 的抽象基类。

设计原则：
- 每个Worker只做一件事（单一职责）
- Worker分级用模型：简单任务用 qwen3.6-plus，深度任务用 qwen3.6-max-preview
- 输入/输出通过 WorkerInput / WorkerOutput 标准化
"""

import os
import yaml
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from src.utils.logger import logger
from src.core.llm_client import LLMClient

load_dotenv()

# Module-level config cache (mtime-based invalidation)
_config_cache: Optional[dict] = None
_config_mtime: float = 0.0
_CONFIG_PATH = "config/settings.yaml"


def _load_cached_config() -> dict:
    """加载配置，基于文件 mtime 缓存，避免重复 YAML 解析"""
    global _config_cache, _config_mtime
    try:
        current_mtime = os.path.getmtime(_CONFIG_PATH)
        if _config_cache is not None and current_mtime == _config_mtime:
            return _config_cache
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            _config_cache = yaml.safe_load(f)
        _config_mtime = current_mtime
        return _config_cache
    except Exception as e:
        logger.error(f"无法加载配置文件: {e}")
        raise


def clear_config_cache() -> None:
    """Force workers created after a settings save to read the latest config."""
    global _config_cache, _config_mtime
    _config_cache = None
    _config_mtime = 0.0


@dataclass
class WorkerSpec:
    """Worker规格说明"""
    name: str                        # Worker名称
    description: str = ""            # 功能描述
    model_level: str = "fast"        # fast=qwen3.6-plus, deep=qwen3.6-max-preview(思考), vision=qwen3.6-plus
    max_retries: int = 2
    timeout: int = 120               # 秒


@dataclass
class WorkerInput:
    """Worker输入"""
    content: str = ""                # 主要输入文本
    url: str = ""                    # 关联URL
    material_id: str = ""            # 关联素材ID
    parent_id: str = ""              # 父素材ID
    metadata: Dict[str, Any] = field(default_factory=dict)
    extra: Dict[str, Any] = field(default_factory=dict)  # 额外参数


@dataclass
class WorkerOutput:
    """Worker输出"""
    success: bool = True
    content: str = ""                # 主要输出文本
    data: Dict[str, Any] = field(default_factory=dict)  # 结构化输出
    materials: List[Any] = field(default_factory=list)   # 产出的Material对象
    error: str = ""
    elapsed: float = 0.0            # 耗时（秒）


class BaseWorker(ABC):
    """Worker抽象基类"""

    def __init__(self, spec: WorkerSpec = None):
        self.spec = spec or WorkerSpec(name=self.__class__.__name__)
        self.config = self._load_config()
        self._llm_client: Optional[LLMClient] = None

    def _load_config(self) -> dict:
        return _load_cached_config()

    @property
    def llm_client(self) -> LLMClient:
        """延迟初始化 LLMClient"""
        if self._llm_client is None:
            self._llm_client = LLMClient(self.config)
        return self._llm_client

    @property
    def client(self):
        """向后兼容：返回底层 SDK 客户端"""
        return self.llm_client.client

    def get_model(self) -> str:
        """根据model_level返回对应的模型名"""
        models = self.config.get("models", {})
        level = self.spec.model_level

        if level == "fast":
            return models.get("fast", "qwen3.6-plus")
        elif level == "deep":
            return models.get("deep", "qwen3.6-max-preview")
        elif level == "vision":
            return models.get("vision", "qwen3.6-plus")
        else:
            return models.get("fast", "qwen3.6-plus")

    def llm_call(
        self,
        prompt: str,
        system: str = "",
        enable_thinking: bool = False,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """统一的LLM调用接口"""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        model = self.get_model()

        try:
            content = self.llm_client.chat_completion(
                messages=messages,
                model=model,
                stream=False,
                enable_thinking=enable_thinking,
                temperature=temperature,
                timeout=self.spec.timeout,
                max_tokens=max_tokens,
            )
            return content
        except Exception as e:
            logger.error(f"[{self.spec.name}] LLM调用失败 (model={model}): {e}")
            raise

    def llm_call_with_images(
        self,
        prompt: str,
        image_urls: List[str],
        system: str = "",
    ) -> str:
        """视觉模型调用（支持图片输入）"""
        model = self.get_model()

        try:
            return self.llm_client.chat_completion_with_images(
                prompt=prompt,
                image_urls=image_urls,
                model=model,
                system=system,
                timeout=self.spec.timeout,
            )
        except Exception as e:
            logger.error(f"[{self.spec.name}] 视觉模型调用失败: {e}")
            raise

    def run(self, input_data: WorkerInput) -> WorkerOutput:
        """执行Worker，带重试和计时"""
        start = time.time()
        last_error = ""

        for attempt in range(self.spec.max_retries + 1):
            try:
                logger.info(f"[{self.spec.name}] 开始执行 (attempt {attempt+1})")
                output = self.execute(input_data)
                output.elapsed = time.time() - start
                logger.info(f"[{self.spec.name}] 执行完成 ({output.elapsed:.1f}s)")
                return output
            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"[{self.spec.name}] 执行失败 (attempt {attempt+1}): {e}"
                )
                if attempt < self.spec.max_retries:
                    time.sleep(2 ** attempt)  # 指数退避

        return WorkerOutput(
            success=False,
            error=f"Worker {self.spec.name} 失败 (重试{self.spec.max_retries}次): {last_error}",
            elapsed=time.time() - start,
        )

    @abstractmethod
    def execute(self, input_data: WorkerInput) -> WorkerOutput:
        """子类实现的核心逻辑"""
        ...
