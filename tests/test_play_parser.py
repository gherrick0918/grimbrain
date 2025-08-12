import json
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
    return subprocess.run(
        args,
        input=cmds,
        text=True,
        capture_output=True,
        timeout=20,
        cwd=str(main_path.parent),
    )


def test_default_actor(tmp_path):
    pcs = [
        {"name": "Malrick", "ac": 15, "hp": 20, "attacks": [{"name": "Shortsword", "to_hit": 5, "damage_dice": "1d6+3", "type": "melee"}]}
    ]
    pc_file = _write_pc(tmp_path, pcs)
    script = "a Goblin \"Shortsword\"\nend\n"
    res = run_play(script, pc_file, "goblin", seed=1)
    assert "Malrick hits Goblin" in res.stdout


def test_wrong_actor_hint(tmp_path):
    pcs = [
        {"name": "Malrick", "ac": 15, "hp": 20, "attacks": [{"name": "Shortsword", "to_hit": 5, "damage_dice": "1d6+3", "type": "melee"}]},
        {"name": "Brynn", "ac": 14, "hp": 20, "attacks": [{"name": "Shortsword", "to_hit": 4, "damage_dice": "1d6+2", "type": "melee"}]},
    ]
    pc_file = _write_pc(tmp_path, pcs)
    script = "a Malrick Goblin \"Shortsword\"\nq\n"
    res = run_play(script, pc_file, "goblin", seed=1)
    assert "It's Brynn's turn." in res.stdout


def test_downed_actor_error(tmp_path):
    pcs = [
        {"name": "Malrick", "ac": 15, "hp": 20, "attacks": [{"name": "Shortsword", "to_hit": 5, "damage_dice": "1d6+3", "type": "melee"}]},
        {"name": "Brynn", "ac": 14, "hp": 0, "max_hp": 10, "attacks": [{"name": "Shortsword", "to_hit": 4, "damage_dice": "1d6+2", "type": "melee"}]},
    ]
    pc_file = _write_pc(tmp_path, pcs)
    script = "a Brynn Goblin \"Shortsword\"\nq\n"
    res = run_play(script, pc_file, "goblin", seed=1)
    assert "Brynn is at 0 HP and cannot act" in res.stdout
