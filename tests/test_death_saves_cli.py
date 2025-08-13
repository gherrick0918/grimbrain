import json, subprocess, sys, os
from pathlib import Path

def _write_pc(tmp_path):
    pcs = {
        "party": [
            {
                "name": "Mal",
                "ac": 15,
                "hp": 1,
                "attacks": [{"name": "S", "to_hit": 5, "damage_dice": "1d6+3", "type": "melee"}],
            },
            {
                "name": "Brynn",
                "ac": 14,
                "hp": 5,
                "attacks": [{"name": "S", "to_hit": 4, "damage_dice": "1d6+2", "type": "melee"}],
            },
        ]
    }
    path = tmp_path / "pc.json"
    path.write_text(json.dumps(pcs))
    return path

def _run(cmds, pc_file, seed, encounter="goblin"):
    main_path = Path(__file__).resolve().parent.parent / "main.py"
    args = [sys.executable, str(main_path), "--play", "--pc", str(pc_file), "--encounter", encounter, "--seed", str(seed)]
    env = os.environ.copy()
    env["GB_TESTING"] = "1"
    return subprocess.run(args, input=cmds, text=True, capture_output=True, timeout=25, cwd=str(main_path.parent), env=env)

def test_auto_death_save(tmp_path):
    pc_file = _write_pc(tmp_path)
    out = _run("end\nend\nend\nstatus\nq\n", pc_file, seed=12).stdout
    assert "death save" in out

def test_stabilize_stops_rolls(tmp_path):
    pc_file = _write_pc(tmp_path)
    out = _run("end\nend\nstabilize Mal\nend\nstatus\nq\n", pc_file, seed=13).stdout
    assert "Mal is stable" in out
    tail = out.split("Mal is stable")[-1]
    assert "death save" not in tail

def test_heal_clears_down(tmp_path):
    pc_file = _write_pc(tmp_path)
    out = _run("end\nend\npotion Mal\nstatus\nq\n", pc_file, seed=13).stdout
    assert "Mal: 6 HP" in out and "Downed" not in out

def test_damage_while_downed_adds_fail(tmp_path):
    pc_file = _write_pc(tmp_path)
    out = _run("end\nend\nend\nstatus\nq\n", pc_file, seed=13).stdout
    assert "suffers 1 death save failure" in out

def test_crit_while_downed_adds_two(tmp_path):
    pc_file = _write_pc(tmp_path)
    out = _run("end\nend\nend\nstatus\nq\n", pc_file, seed=16).stdout
    assert "suffers 2 death save failures" in out

def test_three_fails_causes_death(tmp_path):
    pc_file = _write_pc(tmp_path)
    out = _run("end\nend\nend\nstatus\nq\n", pc_file, seed=13).stdout
    assert "Mal dies" in out
