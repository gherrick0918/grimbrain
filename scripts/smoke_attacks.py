#!/usr/bin/env python3
import argparse
from pathlib import Path

# If you're running this from repo root, imports should work as-is.
# If not, uncomment the next 3 lines to force-add repo root to sys.path.
# import sys
# repo_root = Path(__file__).resolve().parents[1]
# sys.path.insert(0, str(repo_root))

from grimbrain.codex.weapons import WeaponIndex
from grimbrain.models.pc import PlayerCharacter
from grimbrain.rules.attacks import format_mod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target-ac", type=int, default=None)
    ap.add_argument(
        "--odds-mode",
        choices=["none", "advantage", "disadvantage"],
        default="none",
    )
    args = ap.parse_args()

    idx = WeaponIndex.load(Path("data/weapons.json"))

    c = PlayerCharacter(
        name="Test",
        class_="Fighter",
        abilities={
            "str": 16,
            "dex": 14,
            "con": 12,
            "int": 10,
            "wis": 10,
            "cha": 10,
        },
        proficiency_bonus=2,
        ac=15,
        max_hp=12,
        inventory=[],
        equipped_weapons=["Longsword", "Dagger", "Shortbow"],
        weapon_proficiencies={"simple weapons", "martial weapons"},
    )

    entries = c.attacks(idx, target_ac=args.target_ac, mode=args.odds_mode)

    print("=== Attacks & Spellcasting ===")
    print(f"{'Name':<16} {'Atk':>4}  Damage / Type (props)")
    print("-" * 64)
    for e in entries:
        name = e["name"]
        atk = format_mod(e["attack_bonus"])
        line = f"{name:<16} {atk:>4}  {e['damage']}"
        if e.get("odds"):
            line += f"  [{e['odds']}]"
        props = e["properties"]
        if props:
            line += f"  ({props})"
        print(line)
        if e.get("notes"):
            for n in e["notes"]:
                print(f"  · {n}")


if __name__ == "__main__":
    main()
