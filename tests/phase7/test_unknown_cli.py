import os
import subprocess
import sys
from pathlib import Path

from grimbrain.rules import index


def _build_index(tmp_path: Path) -> Path:
    out = tmp_path / "chroma"
    index.build_index("rules", out)
    return out


def test_unknown_rule_cli(tmp_path):
    chroma = _build_index(tmp_path)
    env = os.environ | {"GB_ENGINE": "data", "GB_RULES_DIR": "rules", "GB_CHROMA_DIR": str(chroma)}
    proc = subprocess.run([sys.executable, "main.py", "bogus"], env=env, text=True, capture_output=True)
    assert proc.returncode == 1
    assert "Unknown rule" in proc.stdout
