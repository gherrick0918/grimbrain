import os
from pathlib import Path

from grimbrain.config_env import load_env


def test_env_loads_dotenv(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("FOO=bar\nOPENAI_API_KEY=from_env_file\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "from_process")
    monkeypatch.delenv("FOO", raising=False)

    load_env()

    assert os.getenv("FOO") == "bar"
    assert os.getenv("OPENAI_API_KEY") == "from_process"


def test_ai_cache_dir_from_env(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("GRIMBRAIN_AI_CACHE_DIR=./.grimbrain_cache\n", encoding="utf-8")

    load_env()

    cache_dir = os.getenv("GRIMBRAIN_AI_CACHE_DIR")
    assert cache_dir
    assert Path(cache_dir) == (tmp_path / ".grimbrain_cache").resolve()
