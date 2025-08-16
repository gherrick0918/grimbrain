import json
import os
import subprocess
import sys
from pathlib import Path


def test_rule_override(tmp_path):
    env = os.environ | {
        "GB_ENGINE": "data",
        "GB_RULES_DIR": "rules",
        "GB_CHROMA_DIR": str(tmp_path / "chroma"),
    }
    subprocess.check_call([sys.executable, "tools/convert_data_to_rules.py"], env=env)
    custom = Path("rules/custom/attack.shortsword.json")
    generated = Path("rules/generated/attack.shortsword.json")
    body = json.loads(generated.read_text())
    body["formulas"]["amount"] = "1"
    custom.write_text(json.dumps(body))
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
        [sys.executable, "main.py", "rules", "show", "attack.shortsword"],
        env=env,
        text=True,
    )
    data = json.loads(out)
    assert data["formulas"]["amount"] == "1"
    custom.unlink()
