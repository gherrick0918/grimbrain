#!/usr/bin/env python3
import argparse
from pathlib import Path
from grimbrain.codex.weapons import WeaponIndex
from grimbrain.rules.attacks import damage_string, crit_damage_string, attack_bonus
from grimbrain.rules.attack_math import hit_probabilities

def pct(x):
    return f"{x*100:.1f}%"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ac", type=int, required=True)
    ap.add_argument("--weapon", required=True)
    ap.add_argument("--str", dest="str_", type=int, default=16)
    ap.add_argument("--dex", type=int, default=14)
    ap.add_argument("--pb", type=int, default=2)
    ap.add_argument("--twohanded", action="store_true")
    args = ap.parse_args()

    class C:
        def __init__(self, s, d, pb):
            self.str_score = s
            self.dex_score = d
            self.proficiency_bonus = pb
            self.proficiencies = {"simple weapons", "martial weapons"}

        def ability_mod(self, k):
            return ({"STR": self.str_score, "DEX": self.dex_score}[k] - 10) // 2

    c = C(args.str_, args.dex, args.pb)
    idx = WeaponIndex.load(Path("data/weapons.json"))
    w = idx.get(args.weapon)

    ab = attack_bonus(c, w)
    norm = damage_string(c, w, two_handed=args.twohanded)
    crit = crit_damage_string(c, w, two_handed=args.twohanded)

    for mode in ("none", "advantage", "disadvantage"):
        p = hit_probabilities(ab, args.ac, mode)
        print(
            f"{w.name} vs AC {args.ac} [{mode}]: hit {pct(p['hit'])} (crit {pct(p['crit'])})  | dmg {norm} / crit {crit}"
        )

if __name__ == "__main__":
    main()
