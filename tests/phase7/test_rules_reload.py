import os
import subprocess
import sys


def test_rules_reload_output(tmp_path):
    chroma = tmp_path / "chroma"
    env = os.environ | {
        "GB_ENGINE": "data",
        "GB_RULES_DIR": "rules",
        "GB_CHROMA_DIR": str(chroma),
    }
    proc = subprocess.run(
        [sys.executable, "main.py", "rules", "reload"],
        env=env,
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0
    out = proc.stdout
    assert "reloaded (" in out
    assert "generated=" in out
    assert "custom=" in out
    assert "idx=" in out
