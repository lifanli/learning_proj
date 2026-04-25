"""Manual OpenAI-compatible smoke test.

This script never stores an API key. Run it explicitly after exporting a key, for example:

    $env:LIVE_LLM_API_KEY="..."
    python test-openai.py
"""

from __future__ import annotations

import os

from openai import OpenAI

api_key = os.getenv("LIVE_LLM_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
if not api_key:
    raise SystemExit("Set LIVE_LLM_API_KEY or DASHSCOPE_API_KEY before running this script.")

client = OpenAI(
    api_key=api_key,
    base_url=os.getenv("LIVE_LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
)
completion = client.chat.completions.create(
    model=os.getenv("LIVE_LLM_MODEL", "qwen3.6-plus"),
    messages=[{"role": "user", "content": "Hello!"}],
    max_tokens=32,
)
print(completion.choices[0].message.content)
