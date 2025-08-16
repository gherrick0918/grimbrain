import json
import os
import subprocess
import sys
from pathlib import Path


def test_mutation_reflected(tmp_path):
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
    path = Path("rules/generated/attack.shortsword.json")
    orig = path.read_text()
    data = json.loads(orig)
    data["formulas"]["amount"] = "1"
    data["effects"][0]["amount"] = "1"
    path.write_text(json.dumps(data))
    subprocess.check_call([sys.executable, "main.py", "rules", "reload"], env=env)
    out = subprocess.check_output(
        [sys.executable, "-m", "grimbrain.rules.cli", "attack.shortsword", "Goblin"],
        env=env,
        text=True,
    )
    path.write_text(orig)
    assert "takes 1 damage" in out
