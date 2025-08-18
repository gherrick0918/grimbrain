import json
import os
import subprocess
import sys


def _write_rule(path, rid):
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "id": rid,
                "kind": "action",
                "cli_verb": rid,
                "effects": [],
                "log_templates": {},
            }
        )
    )


def _make_pack(base, name, rules):
    (base / "pack.json").write_text(
        json.dumps({"name": name, "version": "1", "license": "MIT"})
    )
    rdir = base / "rules"
    rdir.mkdir()
    for rid in rules:
        _write_rule(rdir / f"{rid}.json", rid)


def test_pack_index_and_filter(tmp_path):
    rules_dir = tmp_path / "rules" / "custom"
    rules_dir.mkdir(parents=True)
    _write_rule(rules_dir / "dup.json", "dup")

    pack1 = tmp_path / "pack1"
    pack1.mkdir()
    _make_pack(pack1, "p1", ["dup", "p1rule"])
    pack2 = tmp_path / "pack2"
    pack2.mkdir()
    _make_pack(pack2, "p2", ["dup", "p2rule"])

    env = os.environ.copy()
    env["GB_ENGINE"] = "data"
    env["GB_RULES_DIR"] = str(tmp_path / "rules")
    env["GB_CHROMA_DIR"] = str(tmp_path / "chroma")

    res = subprocess.run(
        [
            sys.executable,
            "main.py",
            "content",
            "reload",
            "--packs",
            f"{pack1},{pack2}",
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    assert res.returncode == 0
    assert res.stdout.count("Conflict") == 1
    assert "'p1': 1" in res.stdout
    assert "'p2': 1" in res.stdout
    assert "'custom': 1" in res.stdout

    res = subprocess.run(
        [sys.executable, "main.py", "rules", "packs"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert "p1@1: 1" in res.stdout
    assert "p2@1: 1" in res.stdout

    res = subprocess.run(
        [
            sys.executable,
            "main.py",
            "content",
            "list",
            "--pack",
            "p1",
            "--type",
            "rule",
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    assert "p1rule" in res.stdout
    assert "dup" not in res.stdout
