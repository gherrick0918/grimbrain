import json
import subprocess
import sys
from pathlib import Path


def run_play(args):
    cmd = [sys.executable, "main.py", "play"] + args
    return subprocess.run(cmd, capture_output=True, text=True)


def test_scripted_fight(tmp_path):
    script = Path("tests/scripts/play_smoke.txt")
    pc = Path("tests/fixtures/pc_basic.json")
    res = run_play([
        "--pc", str(pc),
        "--encounter", "goblin",
        "--seed", "7",
        "--script", str(script),
    ])
    assert res.returncode == 0
    out = res.stdout
    assert "attacks" in out
    assert "takes" in out
    assert "Summary:" in out


def test_unknown_verb_shows_suggestion(tmp_path):
    pc = Path("tests/fixtures/pc_basic.json")
    bad_script = tmp_path / "bad.txt"
    bad_script.write_text("attak Goblin\nattack.shortsword Goblin\n")
    res = run_play([
        "--pc", str(pc),
        "--encounter", "goblin",
        "--seed", "2",
        "--script", str(bad_script),
    ])
    assert "Did you mean:" in res.stdout
    assert res.returncode == 0


def test_json_output():
    script = Path("tests/scripts/play_smoke.txt")
    pc = Path("tests/fixtures/pc_basic.json")
    res = run_play([
        "--pc", str(pc),
        "--encounter", "goblin",
        "--seed", "1",
        "--script", str(script),
        "--json",
    ])
    lines = [l for l in res.stdout.splitlines() if l.startswith("{")]
    assert lines, res.stdout
    first = json.loads(lines[0])
    assert first.get("event") == "turn"
