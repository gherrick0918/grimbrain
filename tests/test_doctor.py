import json
import os
import subprocess
import sys


def _write_rule(path, rid, tmpl="{actor.name}"):
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "id": rid,
                "kind": "action",
                "cli_verb": rid,
                "effects": [{"op": "damage", "target": "target", "amount": "1d4"}],
                "log_templates": {"start": tmpl},
            }
        )
    )


def test_rules_doctor(tmp_path):
    rules_dir = tmp_path / "rules" / "custom"
    rules_dir.mkdir(parents=True)
    _write_rule(rules_dir / "good.json", "good")
    _write_rule(rules_dir / "bad.json", "bad", tmpl="{bad.token}")

    env = os.environ.copy()
    env["GB_RULES_DIR"] = str(tmp_path / "rules")
    env["GB_ENGINE"] = "data"

    res = subprocess.run(
        [sys.executable, "main.py", "rules", "doctor"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert res.returncode == 0
    assert "WARN" in res.stdout and "bad" in res.stdout

    res = subprocess.run(
        [sys.executable, "main.py", "rules", "doctor", "--fail-warn"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert res.returncode == 1
