import json
import subprocess
import sys


def run_play(args):
    cmd = [sys.executable, "main.py", "play"] + args
    return subprocess.run(cmd, capture_output=True, text=True, input="")


def test_json_only_stdout():
    res = run_play([
        "--pc", "tests/fixtures/pc_basic.json",
        "--encounter", "goblin",
        "--seed", "7",
        "--json",
        "--quiet",
    ])
    lines = [l for l in res.stdout.splitlines() if l]
    assert lines, res.stdout
    assert all(l.startswith("{") for l in lines), res.stdout
    last = json.loads(lines[-1])
    assert last.get("event") == "summary"
    assert "Indexed" not in res.stdout
    assert "Conflict:" not in res.stdout
    assert ("Indexed" in res.stderr) or ("Conflict:" in res.stderr)
