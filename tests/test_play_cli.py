import json
import subprocess
import sys
from pathlib import Path


def _write_pc(tmp_path: Path, pcs: list[dict]) -> Path:
    path = tmp_path / "pc.json"
    path.write_text(json.dumps({"party": pcs}))
    return path


def run_play(cmds: str, pc_file: Path, encounter: str, seed: int | None = None, packs: str | None = None, cwd: str | None = None) -> subprocess.CompletedProcess:
    """Run the play CLI in a subprocess and capture its output.

    Using ``sys.executable`` ensures the subprocess uses the same Python
    interpreter as the tests, which is important on platforms like Windows
    where ``python`` might not point to the active virtual environment.
    The path to ``main.py`` is resolved relative to this test file so that the
    test can be executed from any working directory.
    """

    main_path = Path(__file__).resolve().parent.parent / "main.py"
    args = [sys.executable, str(main_path), "--play", "--pc", str(pc_file), "--encounter", encounter]
    if packs:
        args += ["--packs", packs]
    if seed is not None:
        args += ["--seed", str(seed)]
    if cwd is None:
        cwd_val = str(main_path.parent)
    else:
        cwd_val = cwd
    proc = subprocess.run(
        args,
        input=cmds,
        text=True,
        capture_output=True,
        timeout=20,
        cwd=cwd_val,
    )
    return proc


def test_basic_attack_flow(tmp_path):
    pcs = [
        {"name": "Malrick", "ac": 15, "hp": 20, "attacks": [{"name": "Shortsword", "to_hit": 5, "damage_dice": "1d6+3", "type": "melee"}]}
    ]
    pc_file = _write_pc(tmp_path, pcs)
    script = "s\na Goblin \"Shortsword\"\ns\nend\n"
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
    script = "c \"Fireball\" all\nend\n"
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
    script = "s\na Goblin \"Shortsword\"\nend\n"
    res1 = run_play(script, pc_file, "goblin", seed=42)
    res2 = run_play(script, pc_file, "goblin", seed=42)
    assert res1.stdout == res2.stdout


def test_typo_and_actions(tmp_path):
    pcs = [
        {"name": "Malrick", "ac": 15, "hp": 20, "attacks": [{"name": "Shortsword", "to_hit": 5, "damage_dice": "1d6+3", "type": "melee"}]}
    ]
    pc_file = _write_pc(tmp_path, pcs)
    script = "attak Goblin \"Shortsword\"\nactions\nq\n"
    res = run_play(script, pc_file, "goblin", seed=1)
    out = res.stdout
    assert "Malrick hits Goblin" in out
    assert "Shortsword" in out


def test_homebrew_pack(tmp_path):
    pcs = [
        {"name": "Malrick", "ac": 15, "hp": 20, "attacks": [{"name": "Shortsword", "to_hit": 5, "damage_dice": "1d6+3", "type": "melee"}]}
    ]
    pc_file = _write_pc(tmp_path, pcs)
    # Create a homebrew pack with a Tiny Dragon monster
    homebrew_dir = tmp_path / "homebrew"
    homebrew_dir.mkdir(parents=True, exist_ok=True)
    tiny_dragon = {
        "name": "Tiny Dragon",
        "source": "HB",
        "ac": "15",
        "hp": "10",
        "speed": "30 ft.",
        "str": 10,
        "dex": 14,
        "con": 12,
        "int": 8,
        "wis": 12,
        "cha": 14,
        "traits": [],
        "actions": [{"name": "Bite", "text": "The dragon bites."}],
        "actions_struct": [],
        "reactions": [],
        "provenance": []
    }
    (homebrew_dir / "tiny dragon.json").write_text(json.dumps(tiny_dragon))
    script = "a \"Tiny Dragon\" \"Shortsword\"\nend\n"
    # Set cwd=tmp_path so the CLI finds the homebrew pack
    res = run_play(script, pc_file, "Tiny Dragon", seed=1, packs=str(tmp_path), cwd=str(tmp_path))
    out = res.stdout
    assert "Tiny Dragon" in out

