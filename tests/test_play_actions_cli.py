import json
import os
import subprocess
import sys
from pathlib import Path


def _write_pc(tmp_path, party):
    path = tmp_path / "pc.json"
    path.write_text(json.dumps({"party": party}))
    return path


def run_play(cmds: str, pc_file: Path, encounter: str, seed: int | None = None) -> subprocess.CompletedProcess:
    main_path = Path(__file__).resolve().parent.parent / "main.py"
    args = [sys.executable, str(main_path), "--play", "--pc", str(pc_file), "--encounter", encounter]
    if seed is not None:
        args += ["--seed", str(seed)]
    env = os.environ.copy()
    env["GB_TESTING"] = "1"
    return subprocess.run(
        args,
        input=cmds,
        text=True,
        capture_output=True,
        timeout=20,
        cwd=str(main_path.parent),
        env=env,
    )


def _party():
    return [
        {
            "name": "Malrick",
            "ac": 15,
            "hp": 20,
            "attacks": [{"name": "Shortsword", "to_hit": 5, "damage_dice": "1d6+3", "type": "melee"}],
        },
        {
            "name": "Brynn",
            "ac": 14,
            "hp": 15,
            "attacks": [{"name": "Shortsword", "to_hit": 4, "damage_dice": "1d6+2", "type": "melee"}],
        },
    ]


def test_dodge_disadvantage(tmp_path):
    pc_file = _write_pc(tmp_path, _party())
    script = "end\ndodge\nend\nq\n"
    res = run_play(script, pc_file, "goblin", seed=5)
    out = res.stdout
    assert "Brynn takes the Dodge action" in out
    assert "[dbg] adv_mode=dis" in out


def test_help_consumed(tmp_path):
    pc_file = _write_pc(tmp_path, _party())
    script = (
        "end\n"
        "help Malrick\nstatus\nend\n"
        'a Goblin "Shortsword"\nstatus\nend\nend\nq\n'
    )
    res = run_play(script, pc_file, "goblin", seed=5)
    out = res.stdout
    assert "Brynn helps Malrick" in out
    assert out.count("[Help]") == 1


def test_hide_consumed(tmp_path):
    pc_file = _write_pc(tmp_path, _party())
    script = (
        "hide\nstatus\n"
        'a Goblin "Shortsword"\nstatus\nend\nend\nq\n'
    )
    res = run_play(script, pc_file, "goblin", seed=5)
    out = res.stdout
    assert "Malrick hides" in out
    assert out.count("[Hidden]") == 1
