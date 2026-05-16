"""Manual OpenAI-compatible smoke test.

This script never stores an API key. Run it explicitly after exporting a key, for example:

    $env:LIVE_LLM_API_KEY="..."
    python test-openai.py
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

api_key = os.getenv("LIVE_LLM_API_KEY") or os.getenv("XIAOMI_MIMO_API_KEY")
if not api_key:
    raise SystemExit("Set LIVE_LLM_API_KEY or XIAOMI_MIMO_API_KEY before running this script.")

client = OpenAI(
    api_key=api_key,
    base_url=os.getenv("LIVE_LLM_BASE_URL", "https://token-plan-cn.xiaomimimo.com/v1"),
)
completion = client.chat.completions.create(
    model=os.getenv("LIVE_LLM_MODEL", "mimo-v2.5"),
    messages=[{"role": "user", "content": "Reply exactly: OK"}],
    max_tokens=32,
    extra_body={"chat_template_kwargs": {"enable_thinking": False}},
)
print(completion.choices[0].message.content)
