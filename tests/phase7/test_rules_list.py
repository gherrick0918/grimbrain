import os
import subprocess
import sys


def test_rules_list_sorted(tmp_path):
    env = os.environ | {
        "GB_ENGINE": "data",
        "GB_RULES_DIR": "rules",
        "GB_CHROMA_DIR": str(tmp_path / "chroma"),
    }
    subprocess.check_call([sys.executable, "tools/convert_data_to_rules.py"], env=env)
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "grimbrain.rules.index",
            "--rules",
            env["GB_RULES_DIR"],
            "--out",
            env["GB_CHROMA_DIR"],
        ],
        env=env,
    )
    out = subprocess.check_output(
        [sys.executable, "main.py", "rules", "list"], env=env, text=True
    )
    lines = [line.strip() for line in out.splitlines() if line.strip()]
    assert lines == sorted(lines)
    assert all("  " in line and "/" in line.split("  ")[1] for line in lines)
