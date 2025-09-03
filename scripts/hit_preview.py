#!/usr/bin/env python3
import argparse
from pathlib import Path
from grimbrain.codex.weapons import WeaponIndex
from grimbrain.rules.attacks import (
    damage_string,
    crit_damage_string,
    build_attacks_block,
)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ac", type=int, required=True)
    ap.add_argument("--weapon", required=True)
    ap.add_argument("--str", dest="str_", type=int, default=16)
    ap.add_argument("--dex", type=int, default=14)
    ap.add_argument("--pb", type=int, default=2)
    ap.add_argument("--twohanded", action="store_true")
    ap.add_argument("--distance", type=int, default=None, help="Target distance in feet")
    ap.add_argument(
        "--cover",
        choices=["none", "half", "three-quarters", "total"],
        default="none",
    )
    args = ap.parse_args()

    class C:
        def __init__(self, s, d, pb):
            self.str_score = s
            self.dex_score = d
            self.proficiency_bonus = pb
            self.proficiencies = {"simple weapons", "martial weapons"}

        def ability_mod(self, k):
            return ({"STR": self.str_score, "DEX": self.dex_score}[k] - 10) // 2

        def ammo_count(self, _):
            return 0

    c = C(args.str_, args.dex, args.pb)
    idx = WeaponIndex.load(Path("data/weapons.json"))
    w = idx.get(args.weapon)
    c.equipped_weapons = [w.name]

    norm = damage_string(c, w, two_handed=args.twohanded)
    crit = crit_damage_string(c, w, two_handed=args.twohanded)

    for mode in ("none", "advantage", "disadvantage"):
        block = build_attacks_block(
            c,
            idx,
            target_ac=args.ac,
            mode=mode,
            target_distance=args.distance,
            cover=args.cover,
        )
        odds = block[0]["odds"] if block else ""
        print(
            f"{w.name} vs AC {args.ac} [{mode}]: {odds}  | dmg {norm} / crit {crit}"
        )

if __name__ == "__main__":
    main()
