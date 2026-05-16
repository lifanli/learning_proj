import os
from pathlib import Path

import pytest
from dotenv import load_dotenv


def test_live_llm_chat_smoke():
    """Manual smoke test; disabled unless RUN_LIVE_LLM_TEST=1 is set."""
    if os.getenv("RUN_LIVE_LLM_TEST") != "1":
        pytest.skip("Set RUN_LIVE_LLM_TEST=1 to run the live LLM smoke test.")

    load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")
    api_key_env = os.getenv("LIVE_LLM_API_KEY_ENV", "XIAOMI_MIMO_API_KEY")
    api_key = os.getenv(api_key_env)
    if not api_key:
        pytest.skip(f"Environment variable {api_key_env} is not set.")

    from openai import OpenAI

    client = OpenAI(
        api_key=api_key,
        base_url=os.getenv("LIVE_LLM_BASE_URL", "https://token-plan-cn.xiaomimimo.com/v1"),
    )
    response = client.chat.completions.create(
        model=os.getenv("LIVE_LLM_MODEL", "mimo-v2.5"),
        messages=[{"role": "user", "content": "Reply exactly: OK"}],
        max_tokens=16,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )

    assert response.choices[0].message.content
