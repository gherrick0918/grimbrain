import json, subprocess, sys, os
from pathlib import Path

from main import heal_target
from grimbrain.engine.combat import Combatant


def _write_pc(tmp_path):
    pcs = {
        "party": [
            {
                "name": "Mal",
                "ac": 15,
                "hp": 1,
                "max_hp": 10,
                "attacks": [{"name": "S", "to_hit": 5, "damage_dice": "1d6+3", "type": "melee"}],
            },
            {
                "name": "Brynn",
                "ac": 14,
                "hp": 5,
                "max_hp": 10,
                "attacks": [{"name": "S", "to_hit": 4, "damage_dice": "1d6+2", "type": "melee"}],
            },
        ]
    }
    path = tmp_path / "pc.json"
    path.write_text(json.dumps(pcs))
    return path


def _run(cmds, pc_file, seed, encounter="goblin"):
    main_path = Path(__file__).resolve().parent.parent / "main.py"
    args = [
        sys.executable,
        str(main_path),
        "--play",
        "--pc",
        str(pc_file),
        "--encounter",
        encounter,
        "--seed",
        str(seed),
    ]
    env = os.environ.copy()
    env["GB_TESTING"] = "1"
    return subprocess.run(
        args,
        input=cmds,
        text=True,
        capture_output=True,
        timeout=25,
        cwd=str(main_path.parent),
        env=env,
    )


def test_heal_logs_clear_from_zero():
    a = Combatant("A", 10, 0, [], "party", max_hp=10)
    msg = heal_target(a, 5)
    assert msg.endswith("; death saves cleared")
    b = Combatant("B", 10, 5, [], "party", max_hp=10)
    msg2 = heal_target(b, 5)
    assert "death saves cleared" not in msg2


def test_corpse_lock_messages(tmp_path):
    pc_file = _write_pc(tmp_path)
    script = (
        "end\nend\nend\n"
        "stabilize Mal\n"
        "heal Mal 3\n"
        "use \"Potion of Healing\" on Mal\n"
        "status\nq\n"
    )
    out = _run(script, pc_file, seed=13).stdout
    tail = out.split("Mal dies")[-1]
    assert tail.count("Mal is dead.") == 3


def test_potion_routes_to_heal_helper(tmp_path):
    pc_file = _write_pc(tmp_path)
    script = "end\nend\nuse \"Potion of Healing\" on Mal\nstatus\nq\n"
    out = _run(script, pc_file, seed=13).stdout
    assert "Potion of Healing on Mal: rolled 2d4+2 =" in out
    assert "Mal heals" in out
    assert "HP 0 →" in out
    assert "death saves cleared" in out
