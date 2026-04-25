import os

import pytest


def test_live_llm_chat_smoke():
    """Manual smoke test; disabled unless RUN_LIVE_LLM_TEST=1 is set."""
    if os.getenv("RUN_LIVE_LLM_TEST") != "1":
        pytest.skip("Set RUN_LIVE_LLM_TEST=1 to run the live LLM smoke test.")

    api_key_env = os.getenv("LIVE_LLM_API_KEY_ENV", "DASHSCOPE_API_KEY")
    api_key = os.getenv(api_key_env)
    if not api_key:
        pytest.skip(f"Environment variable {api_key_env} is not set.")

    from openai import OpenAI

    client = OpenAI(
        api_key=api_key,
        base_url=os.getenv("LIVE_LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    )
    response = client.chat.completions.create(
        model=os.getenv("LIVE_LLM_MODEL", "qwen3.6-plus"),
        messages=[{"role": "user", "content": "hello"}],
        max_tokens=16,
    )

    assert response.choices[0].message.content
