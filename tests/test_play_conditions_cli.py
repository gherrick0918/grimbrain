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
            "attacks": [
                {"name": "Shortsword", "to_hit": 5, "damage_dice": "1d6+3", "type": "melee"},
                {"name": "Shortbow", "to_hit": 5, "damage_dice": "1d6+3", "type": "ranged"},
            ],
        },
        {
            "name": "Brynn",
            "ac": 14,
            "hp": 15,
            "attacks": [
                {"name": "Shortsword", "to_hit": 4, "damage_dice": "1d6+2", "type": "melee"},
                {"name": "Shortbow", "to_hit": 4, "damage_dice": "1d6+2", "type": "ranged"},
            ],
        },
    ]


def test_conditions_cli(tmp_path):
    pc_file = _write_pc(tmp_path, _party())
    # 1) prone grants melee adv and ranged dis
    script1 = (
        "shove Goblin prone\nstatus\nend\n"
        'a Goblin "Shortbow"\nend\n'
        'a Goblin "Shortsword"\nq\n'
    )
    res1 = run_play(script1, pc_file, "goblin", seed=5)
    out1 = res1.stdout
    assert "[Prone]" in out1
    assert "[dbg] adv_mode=adv" in out1
    assert "[dbg] adv_mode=dis" in out1

    # 2) grapple persists across turns and gives no adv/dis
    script2 = (
        "grapple Goblin\nstatus\nend\nend\nstatus\nq\n"
    )
    res2 = run_play(script2, pc_file, "goblin", seed=5)
    out2 = res2.stdout
    assert out2.count("[Grappled]") >= 2
    assert "[dbg] adv_mode=normal" in out2

    # 3) saving throw and stand clearing prone
    script3 = (
        "save Brynn DEX 13\nshove Brynn prone\nend\nend\nstand\nstatus\nq\n"
    )
    res3 = run_play(script3, pc_file, "goblin", seed=4)
    out3 = res3.stdout
    assert "Brynn DEX save" in out3 and "total" in out3
    tail = out3.split("status\n")[-1]
    assert "[Prone]" not in tail
