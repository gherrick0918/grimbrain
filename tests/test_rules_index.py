import json
import subprocess
import sys


def _run_index(tmp_path, adapter: str):
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    if adapter == "rules-json":
        (rules_dir / "foo.json").write_text(json.dumps({"id": "foo"}))
    else:
        weapons = [{"name": "Sword", "range": "melee"}]
        (rules_dir / "weapons.json").write_text(json.dumps(weapons))
    out_dir = tmp_path / "out"
    cmd = [
        sys.executable,
        "-m",
        "grimbrain.rules.index",
        "--rules",
        str(rules_dir),
        "--out",
        str(out_dir),
        "--adapter",
        adapter,
    ]
    return subprocess.run(cmd, capture_output=True, text=True)


def test_rules_index_rules_json(tmp_path):
    res = _run_index(tmp_path, "rules-json")
    assert res.returncode == 0
    assert "Indexed" in res.stdout


def test_rules_index_legacy_data(tmp_path):
    res = _run_index(tmp_path, "legacy-data")
    assert res.returncode == 0
    assert "Indexed" in res.stdout

