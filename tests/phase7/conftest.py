import os
import shutil
from pathlib import Path
import subprocess
import sys
import pytest


@pytest.fixture
def env_setup(tmp_path):
    root = Path(__file__).resolve().parents[2]
    rules_src = root / "rules"
    data_src = root / "data"
    rules_dir = tmp_path / "rules"
    shutil.copytree(rules_src, rules_dir)
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    for name in ["weapons.json", "spells.json", "monsters.json"]:
        shutil.copy(data_src / name, data_dir / name)
    chroma_dir = tmp_path / ".chroma"
    env = os.environ.copy()
    env["GB_ENGINE"] = "data"
    env["GB_RULES_DIR"] = str(rules_dir)
    env["GB_DATA_DIR"] = str(data_dir)
    env["GB_CHROMA_DIR"] = str(chroma_dir)
    # initial index
    subprocess.run([sys.executable, "main.py", "content", "reload"], cwd=root, env=env, check=True, capture_output=True)
    return env, root, data_dir
