import json
import subprocess
from pathlib import Path


def _write_pc(tmp_path: Path, pcs: list[dict]) -> Path:
    path = tmp_path / "pc.json"
    path.write_text(json.dumps({"party": pcs}))
    return path


def run_play(cmds: str, pc_file: Path, encounter: str, seed: int | None = None) -> subprocess.CompletedProcess:
    args = ["python", "main.py", "--play", "--pc", str(pc_file), "--encounter", encounter]
    if seed is not None:
        args += ["--seed", str(seed)]
    proc = subprocess.run(args, input=cmds, text=True, capture_output=True, timeout=20)
    return proc


def test_basic_attack_flow(tmp_path):
    pcs = [
        {"name": "Malrick", "ac": 15, "hp": 20, "attacks": [{"name": "Shortsword", "to_hit": 5, "damage_dice": "1d6+3", "type": "melee"}]}
    ]
    pc_file = _write_pc(tmp_path, pcs)
    script = "status\nattack Malrick Goblin \"Shortsword\"\nstatus\nend\n"
    res = run_play(script, pc_file, "goblin", seed=1)
    out = res.stdout
    assert "Malrick hits Goblin" in out
    lines = [l for l in out.splitlines() if l.startswith("Goblin:")]
    assert len(lines) == 2
    def _hp(line: str) -> int:
        parts = line.split()
        return 0 if parts[1] == "DEFEATED," else int(parts[1])
    hp_vals = [_hp(l) for l in lines]
    assert hp_vals[1] < hp_vals[0]


def test_cast_fireball_flow(tmp_path):
    pcs = [
        {"name": "Brynn", "ac": 14, "hp": 16, "attacks": [
            {"name": "Fireball", "damage_dice": "8d6", "type": "spell", "save_dc": 14, "save_ability": "dex"}
        ]}
    ]
    pc_file = _write_pc(tmp_path, pcs)
    script = "cast Brynn \"Fireball\" all\nend\n"
    res = run_play(script, pc_file, "goblin x2", seed=2)
    out = res.stdout
    assert out.count("Dex save") == 2
    dmg = [int(d) for d in __import__("re").findall(r"Fireball hits Goblin for (\d+)", out)]
    assert len(dmg) == 2
    dmg.sort()
    assert dmg[1] == dmg[0] * 2 or dmg[0] == dmg[1]


def test_seed_determinism(tmp_path):
    pcs = [
        {"name": "Malrick", "ac": 15, "hp": 20, "attacks": [{"name": "Shortsword", "to_hit": 5, "damage_dice": "1d6+3", "type": "melee"}]}
    ]
    pc_file = _write_pc(tmp_path, pcs)
    script = "status\nattack Malrick Goblin \"Shortsword\"\nend\n"
    res1 = run_play(script, pc_file, "goblin", seed=42)
    res2 = run_play(script, pc_file, "goblin", seed=42)
    assert res1.stdout == res2.stdout

