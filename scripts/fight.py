#!/usr/bin/env python3
import argparse
from pathlib import Path
from grimbrain.engine.types import Combatant
from grimbrain.engine.round import run_encounter
from grimbrain.character import Character
from grimbrain.codex.weapons import WeaponIndex


def make_char(str_, dex, pb, styles, feats, profs):
    return Character(str_score=str_, dex_score=dex, proficiency_bonus=pb,
                     fighting_styles=set(styles), feats=set(feats),
                     proficiencies=set(profs))


def main():
    ap = argparse.ArgumentParser(description="Grimbrain duel (turn-based)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--rounds", type=int, default=20)
    # A
    ap.add_argument("--a-name", default="A")
    ap.add_argument("--a-str", type=int, default=16)
    ap.add_argument("--a-dex", type=int, default=14)
    ap.add_argument("--a-pb",  type=int, default=2)
    ap.add_argument("--a-styles", nargs="*", default=[])
    ap.add_argument("--a-feats",  nargs="*", default=[])
    ap.add_argument("--a-profs",  nargs="*", default=["simple weapons","martial weapons"])
    ap.add_argument("--a-hp", type=int, default=20)
    ap.add_argument("--a-weapon", required=True)
    ap.add_argument("--a-offhand", default=None)
    ap.add_argument("--a-distance", type=int, default=None)
    ap.add_argument("--a-cover", choices=["none","half","three-quarters","total"], default="none")
    # B
    ap.add_argument("--b-name", default="B")
    ap.add_argument("--b-str", type=int, default=16)
    ap.add_argument("--b-dex", type=int, default=14)
    ap.add_argument("--b-pb",  type=int, default=2)
    ap.add_argument("--b-styles", nargs="*", default=[])
    ap.add_argument("--b-feats",  nargs="*", default=[])
    ap.add_argument("--b-profs",  nargs="*", default=["simple weapons","martial weapons"])
    ap.add_argument("--b-hp", type=int, default=20)
    ap.add_argument("--b-weapon", required=True)
    ap.add_argument("--b-offhand", default=None)
    ap.add_argument("--b-distance", type=int, default=None)
    ap.add_argument("--b-cover", choices=["none","half","three-quarters","total"], default="none")

    args = ap.parse_args()

    widx = WeaponIndex.load(Path("data/weapons.json"))

    actor_a = make_char(args.a_str, args.a_dex, args.a_pb, args.a_styles, args.a_feats, args.a_profs)
    actor_b = make_char(args.b_str, args.b_dex, args.b_pb, args.b_styles, args.b_feats, args.b_profs)

    def _add_ammo(actor, weapon_name):
        if not weapon_name:
            return
        w = widx.get(weapon_name)
        ammo = w.ammo_type()
        if ammo:
            actor.add_ammo(ammo, 20)

    _add_ammo(actor_a, args.a_weapon)
    _add_ammo(actor_a, args.a_offhand)
    _add_ammo(actor_b, args.b_weapon)
    _add_ammo(actor_b, args.b_offhand)

    A = Combatant(
        name=args.a_name,
        actor=actor_a,
        hp=args.a_hp,
        weapon=args.a_weapon,
        offhand=args.a_offhand,
        distance_ft=args.a_distance,
        cover=args.a_cover
    )
    B = Combatant(
        name=args.b_name,
        actor=actor_b,
        hp=args.b_hp,
        weapon=args.b_weapon,
        offhand=args.b_offhand,
        distance_ft=args.b_distance,
        cover=args.b_cover
    )

    res = run_encounter(A, B, seed=args.seed, max_rounds=args.rounds)
    print("\n".join(res["log"]))
    print(f"\nResult: winner = {res['winner']} (A_hp={res['a_hp']}  B_hp={res['b_hp']}) after {res['rounds']} round(s)")


if __name__ == "__main__":
    main()

