#!/usr/bin/env python3
import argparse, random
from pathlib import Path
from grimbrain.codex.weapons import WeaponIndex
from grimbrain.character import Character
from grimbrain.engine.types import Target
from grimbrain.engine.combat import resolve_attack
from grimbrain.engine.damage import apply_defenses


def main():
    ap = argparse.ArgumentParser(description="Grimbrain single attack demo")
    ap.add_argument("--weapon", required=True)
    ap.add_argument("--ac", type=int, required=True)
    ap.add_argument("--hp", type=int, default=10)
    ap.add_argument("--distance", type=int, default=None)
    ap.add_argument("--cover", choices=["none","half","three-quarters","total"], default="none")
    ap.add_argument("--mode", choices=["none","advantage","disadvantage"], default="none")
    ap.add_argument("--power", action="store_true", help="-5/+10 if eligible (SS/GWM)")
    ap.add_argument("--offhand", action="store_true")
    ap.add_argument("--twohanded", action="store_true")
    ap.add_argument("--dex", type=int, default=16)
    ap.add_argument("--str", type=int, default=16)
    ap.add_argument("--pb", type=int, default=2)
    ap.add_argument("--styles", nargs="*", default=[], help='e.g. Archery Dueling "Two-Weapon Fighting"')
    ap.add_argument("--feats", nargs="*", default=[], help="e.g. Sharpshooter 'Great Weapon Master'")
    ap.add_argument("--ammo", nargs="*", default=[], help="pairs like arrows:20 bolts:10")
    ap.add_argument("--target-resist", nargs="*", default=[], help="damage types")
    ap.add_argument("--target-vulnerable", nargs="*", default=[], help="damage types")
    ap.add_argument("--target-immune", nargs="*", default=[], help="damage types")
    ap.add_argument("--target-thp", type=int, default=0)
    args = ap.parse_args()

    # quick character stub
    c = Character(str_score=args.str, dex_score=args.dex, proficiency_bonus=args.pb,
                  proficiencies={"simple weapons","martial weapons"},
                  fighting_styles=set(args.styles), equipped_weapons=[args.weapon],
                  ammo={k:int(v) for k,v in (x.split(":",1) for x in args.ammo)})

    idx = WeaponIndex.load(Path("data/weapons.json"))
    tgt = Target(ac=args.ac, hp=args.hp, cover=args.cover, distance_ft=args.distance)

    res = resolve_attack(c, args.weapon, tgt, idx,
                         base_mode=args.mode, power=args.power,
                         offhand=args.offhand, two_handed=args.twohanded,
                         has_fired_loading_weapon_this_turn=False, rng=random.Random())

    if not res.get("ok"):
        print(f"Attack not possible: {res.get('reason')} [{', '.join(res.get('notes', []))}]")
        return

    print(f"{res['weapon']} vs AC {res['effective_ac']} [{args.mode}]  notes: {', '.join(res['notes']) if res['notes'] else '-'}")
    cands = "/".join(map(str, res['candidates']))
    print(f"  d20: {res['d20']} (candidates {cands})  AB {res['attack_bonus']}  =>  {'CRIT' if res['is_crit'] else ('HIT' if res['is_hit'] else 'MISS')}")
    print(f"  damage ({res['damage_string']}): rolls={res['damage']['rolls']} sum={res['damage']['sum_dice']} mod={res['damage']['mod']}  TOTAL={res['damage']['total']}")
    if res['spent_ammo']:
        print("  ammo: spent 1")

    class _Def:
        def __init__(self):
            self.resist = set(args.target_resist)
            self.vulnerable = set(args.target_vulnerable)
            self.immune = set(args.target_immune)
            self.temp_hp = args.target_thp

    w = idx.get(args.weapon)
    final, notes2, _ = apply_defenses(res["damage"]["total"], w.damage_type, _Def())
    print(f"  effective after defenses: {final}  ({'; '.join(notes2) if notes2 else 'no defenses'})")


if __name__ == "__main__":
    main()
