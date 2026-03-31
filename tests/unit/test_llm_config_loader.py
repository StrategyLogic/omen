from pathlib import Path

import pytest

from omen.ingest.llm_ontology.config import load_llm_config


def test_load_llm_config_falls_back_to_env_without_file(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-key")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    monkeypatch.setenv("DEEPSEEK_CHAT_MODEL", "deepseek-chat")
    monkeypatch.setenv("VOYAGE_API_KEY", "voyage-key")

    config = load_llm_config(Path("/tmp/not-exists-llm-config.toml"))

    assert config.deepseek_api_key == "deepseek-key"
    assert config.voyage_api_key == "voyage-key"
    assert config.chat_model == "deepseek-chat"


def test_load_llm_config_chat_only_without_voyage(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-key")
    monkeypatch.setenv("VOYAGE_API_KEY", "")

    config = load_llm_config(Path("/tmp/not-exists-llm-config.toml"))

    assert config.deepseek_api_key == "deepseek-key"
    assert config.voyage_api_key == "chat-only"


def test_load_llm_config_requires_deepseek_key_when_file_missing(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    monkeypatch.setenv("VOYAGE_API_KEY", "")

    with pytest.raises(FileNotFoundError):
        load_llm_config(Path("/tmp/not-exists-llm-config.toml"))
