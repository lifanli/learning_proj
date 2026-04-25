"""
统一 LLM 客户端
================
根据 config.llm.provider 路由到 OpenAI SDK 或 Anthropic SDK。

支持的 provider:
- "openai": 兼容 OpenAI API 格式（DashScope/Qwen/DeepSeek 等）
- "anthropic": Anthropic Claude API

对外接口保持一致，调用方无需关心底层 SDK 差异。
"""

import os
from typing import List, Optional, Generator, Tuple, Union
from urllib.parse import urlparse

from dotenv import load_dotenv
from src.utils.logger import logger

load_dotenv()

# 尝试导入 anthropic SDK，不可用时设为 None
try:
    import anthropic as _anthropic_module
except ImportError:
    _anthropic_module = None


class LLMClient:
    """统一 LLM 客户端，屏蔽 OpenAI / Anthropic SDK 差异"""

    def __init__(self, config: dict):
        """
        Args:
            config: 完整的 settings.yaml 配置字典
        """
        self._config = config
        self._provider = config.get("llm", {}).get("provider", "openai")
        self._client = None

        # 如果指定 anthropic 但未安装 SDK，回退到 openai
        if self._provider == "anthropic" and _anthropic_module is None:
            logger.warning(
                "[LLMClient] anthropic 包未安装，自动回退到 openai provider。"
                "请运行 pip install anthropic 以使用 Claude API。"
            )
            self._provider = "openai"

    @property
    def provider(self) -> str:
        return self._provider

    @property
    def client(self):
        """延迟初始化底层 SDK 客户端（向后兼容用）"""
        if self._client is None:
            self._client = self._create_client()
        return self._client

    def _create_client(self):
        llm_cfg = self._config.get("llm", {})

        # Prefer environment variables. Direct api_key is kept only for
        # backward compatibility and should not be used in committed config.
        api_key_env = (llm_cfg.get("api_key_env", "") or "").strip()
        api_key = (os.getenv(api_key_env, "") or "").strip() if api_key_env else ""
        if not api_key:
            api_key = str(llm_cfg.get("api_key", "") or "").strip()
        if not api_key:
            hint = f" (环境变量 {api_key_env} 未设置)" if api_key_env else ""
            raise ValueError(
                f"未找到 API Key{hint}。"
                "请设置 llm.api_key_env 指向的环境变量，或临时在本地 config 中设置 api_key。"
            )

        if self._provider == "anthropic":
            kwargs = {"api_key": api_key}
            base_url = llm_cfg.get("base_url")
            if base_url:
                # Anthropic SDK 会自动在路径前加 /v1/，
                # 所以需要去掉 base_url 尾部的 /v1 避免重复
                base_url = base_url.rstrip("/")
                if base_url.endswith("/v1"):
                    base_url = base_url[:-3]
                kwargs["base_url"] = base_url
            return _anthropic_module.Anthropic(**kwargs)
        else:
            from openai import OpenAI
            return OpenAI(
                api_key=api_key,
                base_url=self._normalize_openai_base_url(llm_cfg.get("base_url")),
            )

    # ------------------------------------------------------------------
    # chat_completion: 统一的文本对话接口
    # ------------------------------------------------------------------
    def chat_completion(
        self,
        messages: List[dict],
        model: str,
        stream: bool = False,
        enable_thinking: bool = False,
        temperature: float = 0.7,
        timeout: int = 120,
        max_tokens: Optional[int] = None,
    ) -> Union[str, Generator[Tuple[str, str], None, None]]:
        """
        统一聊天补全接口。

        Args:
            messages: [{"role": "system"|"user"|"assistant", "content": ...}]
            model: 模型名称
            stream: 是否流式返回
            enable_thinking: 是否启用思考模式
            temperature: 采样温度
            timeout: 超时秒数
            max_tokens: 最大输出 token 数

        Returns:
            非流式: str (最终文本内容)
            流式: Generator[Tuple[str, str]] — 产出 ("thinking", text) 或 ("content", text)
        """
        if self._provider == "anthropic":
            return self._anthropic_chat(
                messages, model, stream, enable_thinking,
                temperature, timeout, max_tokens,
            )
        else:
            return self._openai_chat(
                messages, model, stream, enable_thinking,
                temperature, timeout, max_tokens,
            )

    # ------------------------------------------------------------------
    # chat_completion_with_images: 统一的视觉模型接口
    # ------------------------------------------------------------------
    def chat_completion_with_images(
        self,
        prompt: str,
        image_urls: List[str],
        model: str,
        system: str = "",
        timeout: int = 120,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        视觉模型调用（支持图片输入）。

        Args:
            prompt: 文字提示
            image_urls: 图片 URL 列表
            model: 模型名称
            system: 系统提示
            timeout: 超时秒数
            max_tokens: 最大输出 token 数

        Returns:
            str: 模型回复文本
        """
        if self._provider == "anthropic":
            return self._anthropic_vision(
                prompt, image_urls, model, system, timeout, max_tokens,
            )
        else:
            return self._openai_vision(
                prompt, image_urls, model, system, timeout, max_tokens,
            )

    # ==================================================================
    # OpenAI 路径
    # ==================================================================

    def _openai_chat(
        self, messages, model, stream, enable_thinking,
        temperature, timeout, max_tokens,
    ):
        extra_body = {}
        if enable_thinking:
            extra_body["enable_thinking"] = True

        llm_cfg = self._config.get("llm", {})
        effective_max_tokens = max_tokens or llm_cfg.get("max_tokens")

        kwargs = dict(
            model=model,
            messages=messages,
            stream=stream,
            temperature=temperature,
            timeout=timeout,
        )
        if extra_body:
            kwargs["extra_body"] = extra_body
        if effective_max_tokens is not None:
            kwargs["max_tokens"] = effective_max_tokens

        api_mode = llm_cfg.get("api_mode", "auto")
        if api_mode == "responses" and not stream:
            return self._openai_responses_chat(messages, model, effective_max_tokens, timeout)

        try:
            response = self.client.chat.completions.create(**kwargs)
        except Exception as e:
            if api_mode == "auto" and not stream and self._looks_like_not_found(e):
                logger.warning(
                    "[LLMClient] chat.completions 返回 404，自动切换到 responses API。"
                    "如果该中转只支持 Codex/GPT-5 responses，这是正常兼容路径。"
                )
                return self._openai_responses_chat(messages, model, effective_max_tokens, timeout)
            raise

        if stream:
            return self._openai_stream(response)
        else:
            choice = response.choices[0]
            finish_reason = getattr(choice, "finish_reason", None)
            self._raise_if_truncated(finish_reason)
            content = choice.message.content or ""
            return self._strip_think_tags(content)

    def _openai_stream(self, response) -> Generator[Tuple[str, str], None, None]:
        """OpenAI 流式 → 统一 (content_type, text) 元组"""
        for chunk in response:
            delta = chunk.choices[0].delta
            if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                yield ("thinking", delta.reasoning_content)
            if hasattr(delta, "content") and delta.content:
                yield ("content", delta.content)

    def _openai_vision(
        self, prompt, image_urls, model, system, timeout, max_tokens,
    ) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})

        content_parts = [{"type": "text", "text": prompt}]
        for url in image_urls:
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": url},
            })
        messages.append({"role": "user", "content": content_parts})

        kwargs = dict(
            model=model,
            messages=messages,
            stream=False,
            timeout=timeout,
        )
        llm_cfg = self._config.get("llm", {})
        effective_max_tokens = max_tokens or llm_cfg.get("vision_max_tokens") or llm_cfg.get("max_tokens")
        if effective_max_tokens is not None:
            kwargs["max_tokens"] = effective_max_tokens

        response = self.client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        self._raise_if_truncated(getattr(choice, "finish_reason", None))
        return choice.message.content or ""

    def _openai_responses_chat(
        self,
        messages: List[dict],
        model: str,
        max_tokens: Optional[int],
        timeout: int,
    ) -> str:
        structured_kwargs = {
            "model": model,
            "input": self._messages_to_responses_input(messages),
        }
        if max_tokens is not None:
            structured_kwargs["max_output_tokens"] = max_tokens
        if timeout is not None:
            structured_kwargs["timeout"] = timeout

        response = self.client.responses.create(**structured_kwargs)
        text = self._extract_responses_output_text(response)
        if text:
            return self._strip_think_tags(text)

        status = getattr(response, "status", None)
        if status in {"incomplete", "failed"}:
            raise RuntimeError(f"Responses API returned unsuccessful status: {status}")

        # Some custom gateways accept /v1/responses but do not reliably return
        # text for structured role/content input. Retry with a flattened prompt.
        logger.warning(
            "[LLMClient] Responses API returned no text for structured input; "
            "retrying with flattened prompt for compatibility."
        )
        fallback_kwargs = {
            "model": model,
            "input": self._messages_to_responses_prompt(messages),
        }
        if max_tokens is not None:
            fallback_kwargs["max_output_tokens"] = max_tokens
        if timeout is not None:
            fallback_kwargs["timeout"] = timeout

        fallback_response = self.client.responses.create(**fallback_kwargs)
        fallback_text = self._extract_responses_output_text(fallback_response)
        if fallback_text:
            return self._strip_think_tags(fallback_text)

        fallback_status = getattr(fallback_response, "status", None)
        raise RuntimeError(
            "Responses API returned no extractable text output. "
            f"status={fallback_status or status!r}"
        )

    # ==================================================================
    # Anthropic 路径
    # ==================================================================

    def _anthropic_chat(
        self, messages, model, stream, enable_thinking,
        temperature, timeout, max_tokens,
    ):
        # 分离 system 消息
        system_text, user_messages = self._extract_system_for_anthropic(messages)

        anthropic_cfg = self._config.get("llm", {}).get("anthropic", {})
        default_max = anthropic_cfg.get("max_tokens", 8192)

        kwargs = dict(
            model=model,
            messages=user_messages,
            max_tokens=max_tokens or default_max,
            timeout=timeout,
        )

        if system_text:
            kwargs["system"] = system_text

        if enable_thinking:
            budget = anthropic_cfg.get("thinking_budget_tokens", 10000)
            kwargs["thinking"] = {
                "type": "enabled",
                "budget_tokens": budget,
            }
            # Claude 思考模式要求 temperature=1
            kwargs["temperature"] = 1.0
        else:
            kwargs["temperature"] = temperature

        if stream:
            kwargs["stream"] = True
            response = self.client.messages.create(**kwargs)
            return self._anthropic_stream(response)
        else:
            response = self.client.messages.create(**kwargs)
            self._raise_if_truncated(getattr(response, "stop_reason", None))
            return self._extract_anthropic_text(response)

    def _anthropic_stream(self, response) -> Generator[Tuple[str, str], None, None]:
        """Anthropic 流式 → 统一 (content_type, text) 元组"""
        for event in response:
            if event.type == "content_block_delta":
                delta = event.delta
                if delta.type == "thinking_delta":
                    yield ("thinking", delta.thinking)
                elif delta.type == "text_delta":
                    yield ("content", delta.text)

    def _anthropic_vision(
        self, prompt, image_urls, model, system, timeout, max_tokens,
    ) -> str:
        anthropic_cfg = self._config.get("llm", {}).get("anthropic", {})
        default_max = anthropic_cfg.get("max_tokens", 8192)

        content_parts = [{"type": "text", "text": prompt}]
        for url in image_urls:
            content_parts.append(self._build_anthropic_image_block(url))

        kwargs = dict(
            model=model,
            messages=[{"role": "user", "content": content_parts}],
            max_tokens=max_tokens or default_max,
            timeout=timeout,
        )
        if system:
            kwargs["system"] = system

        response = self.client.messages.create(**kwargs)
        self._raise_if_truncated(getattr(response, "stop_reason", None))
        return self._extract_anthropic_text(response)

    # ==================================================================
    # 工具方法
    # ==================================================================

    @staticmethod
    def _normalize_openai_base_url(base_url: Optional[str]) -> Optional[str]:
        """Normalize OpenAI-compatible endpoints to a usable API root."""
        if not base_url:
            return base_url

        normalized = base_url.rstrip("/")
        parsed = urlparse(normalized)
        path = parsed.path.rstrip("/")
        if path in {"", "/"}:
            normalized = normalized + "/v1"
        return normalized

    @staticmethod
    def _extract_system_for_anthropic(messages: List[dict]):
        """从 messages 中分离 system 消息（Anthropic 不支持 system 在 messages 数组中）"""
        system_parts = []
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_parts.append(msg["content"])
            else:
                user_messages.append(msg)
        system_text = "\n\n".join(system_parts) if system_parts else ""
        return system_text, user_messages

    @staticmethod
    def _messages_to_responses_input(messages: List[dict]) -> List[dict]:
        inputs = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if isinstance(content, list):
                content_parts = content
            else:
                content_parts = [{"type": "input_text", "text": str(content)}]
            inputs.append({"role": role, "content": content_parts})
        return inputs

    @staticmethod
    def _messages_to_responses_prompt(messages: List[dict]) -> str:
        parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if isinstance(content, list):
                text = "\n".join(
                    str(block.get("text", ""))
                    for block in content
                    if isinstance(block, dict)
                )
            else:
                text = str(content)
            if text.strip():
                parts.append(f"[{role}]\n{text.strip()}")
        return "\n\n".join(parts)

    @staticmethod
    def _extract_responses_output_text(response) -> str:
        output_text = getattr(response, "output_text", None)
        if output_text:
            return output_text
        return LLMClient._extract_responses_text(response)

    @staticmethod
    def _extract_responses_text(response) -> str:
        parts = []
        for item in getattr(response, "output", []) or []:
            for block in getattr(item, "content", []) or []:
                block_type = getattr(block, "type", "")
                if block_type in {"output_text", "text"}:
                    parts.append(getattr(block, "text", ""))
        return "\n".join(p for p in parts if p)

    @staticmethod
    def _looks_like_not_found(error: Exception) -> bool:
        text = str(error).lower()
        return "404" in text or "not found" in text or "page not found" in text

    @staticmethod
    def _extract_anthropic_text(response) -> str:
        """从 Anthropic 响应中提取文本内容（跳过 thinking blocks）"""
        parts = []
        for block in response.content:
            if block.type == "text":
                parts.append(block.text)
        return "\n".join(parts) if parts else ""

    @staticmethod
    def _raise_if_truncated(finish_reason: Optional[str]) -> None:
        """Fail loudly when the model reports output/context truncation."""
        if finish_reason in {"length", "max_tokens", "model_context_window_exceeded"}:
            raise RuntimeError(
                f"LLM response was truncated by output/context limit: {finish_reason}"
            )

    @staticmethod
    def _build_anthropic_image_block(url: str) -> dict:
        """构建 Anthropic 图片 content block，自动区分 base64 data URI 和 HTTPS URL"""
        if url.startswith("data:"):
            # data:image/png;base64,iVBOR... → 提取 media_type 和 data
            import re
            m = re.match(r"data:(image/[^;]+);base64,(.+)", url, re.DOTALL)
            if m:
                return {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": m.group(1),
                        "data": m.group(2),
                    },
                }
        return {
            "type": "image",
            "source": {"type": "url", "url": url},
        }

    @staticmethod
    def _strip_think_tags(content: str) -> str:
        """去除 <think>...</think> 标签（某些模型会在 content 中混入思考内容）"""
        if "<think>" not in content:
            return content
        import re
        content = re.sub(r"<think>[\s\S]*?</think>", "", content)
        if "<think>" in content:
            content = content.split("<think>")[0]
        return content.strip()
