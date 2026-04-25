import pytest

try:
    from src.storage import rag_manager
except ModuleNotFoundError as exc:
    if exc.name and exc.name.startswith("lightrag"):
        pytest.skip("LightRAG is not installed", allow_module_level=True)
    raise


def test_rag_manager_uses_project_llm_settings(tmp_path, monkeypatch):
    settings_path = tmp_path / "settings.yaml"
    settings_path.write_text(
        "\n".join(
            [
                "llm:",
                "  api_key_env: TEST_RAG_API_KEY",
                "  base_url: https://example.test/v1",
                "  embedding_model: text-embedding-v3",
                "models:",
                "  fast: qwen-test-fast",
                "embedding:",
                "  dimension: 1024",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(rag_manager, "CONFIG_PATH", settings_path)
    monkeypatch.setenv("TEST_RAG_API_KEY", "dummy-rag-key")

    config = rag_manager._resolve_rag_config()

    assert config["api_key"] == "dummy-rag-key"
    assert config["base_url"] == "https://example.test/v1"
    assert config["llm_model"] == "qwen-test-fast"
    assert config["embedding_model"] == "text-embedding-v3"
    assert config["embedding_dim"] == 1024
