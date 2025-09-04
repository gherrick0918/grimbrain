#!/usr/bin/env python3
import argparse
from grimbrain.engine.types import Combatant
from grimbrain.engine.scene import run_scene
from grimbrain.character import Character


def make_char(str_, dex, pb, styles, feats, profs, speed, attacks):
    return Character(
        str_score=str_,
        dex_score=dex,
        proficiency_bonus=pb,
        fighting_styles=set(styles),
        feats=set(feats),
        proficiencies=set(profs),
        speed_ft=speed,
        ammo={"arrows": 99, "bolts": 99},
        attacks=attacks,  # Pass attacks to Character
    )


def main():
    ap = argparse.ArgumentParser(description="Grimbrain scene fight (movement + simple AI)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--rounds", type=int, default=20)
    ap.add_argument("--start", type=int, default=30, help="starting distance (ft)")

    # A
    ap.add_argument("--a-name", default="A")
    ap.add_argument("--a-weapon", required=True)
    ap.add_argument("--a-offhand", default=None)
    ap.add_argument("--a-hp", type=int, default=20)
    ap.add_argument("--a-str", type=int, default=16)
    ap.add_argument("--a-dex", type=int, default=14)
    ap.add_argument("--a-pb", type=int, default=2)
    ap.add_argument("--a-speed", type=int, default=30)
    ap.add_argument("--a-styles", nargs="*", default=[])
    ap.add_argument("--a-feats", nargs="*", default=[])
    ap.add_argument("--a-profs", nargs="*", default=["simple weapons", "martial weapons"])
    ap.add_argument("--a-cover", choices=["none", "half", "three-quarters", "total"], default="none")
    ap.add_argument("--a-attacks", type=int, default=1, help="Attacks per action for A")

    # B
    ap.add_argument("--b-name", default="B")
    ap.add_argument("--b-weapon", required=True)
    ap.add_argument("--b-offhand", default=None)
    ap.add_argument("--b-hp", type=int, default=20)
    ap.add_argument("--b-str", type=int, default=16)
    ap.add_argument("--b-dex", type=int, default=14)
    ap.add_argument("--b-pb", type=int, default=2)
    ap.add_argument("--b-speed", type=int, default=30)
    ap.add_argument("--b-styles", nargs="*", default=[])
    ap.add_argument("--b-feats", nargs="*", default=[])
    ap.add_argument("--b-profs", nargs="*", default=["simple weapons", "martial weapons"])
    ap.add_argument("--b-cover", choices=["none", "half", "three-quarters", "total"], default="none")
    ap.add_argument("--b-attacks", type=int, default=1, help="Attacks per action for B")

    args = ap.parse_args()

    A = Combatant(
        name=args.a_name,
        actor=make_char(
            args.a_str,
            args.a_dex,
            args.a_pb,
            args.a_styles,
            args.a_feats,
            args.a_profs,
            args.a_speed,
            args.a_attacks
        ),
        hp=args.a_hp,
        weapon=args.a_weapon,
        offhand=args.a_offhand,
        distance_ft=None,
        cover=args.a_cover,
        attacks_per_action=args.a_attacks,  # <-- Pass here
    )
    B = Combatant(
        name=args.b_name,
        actor=make_char(
            args.b_str,
            args.b_dex,
            args.b_pb,
            args.b_styles,
            args.b_feats,
            args.b_profs,
            args.b_speed,
            args.b_attacks
        ),
        hp=args.b_hp,
        weapon=args.b_weapon,
        offhand=args.b_offhand,
        distance_ft=None,
        cover=args.b_cover,
        attacks_per_action=args.b_attacks,  # <-- Pass here
    )

    res = run_scene(A, B, seed=args.seed, max_rounds=args.rounds, start_distance_ft=args.start)
    print("\n".join(res.log))
    print(
        f"\nResult: winner = {res.winner} (A_hp={res.a_hp}  B_hp={res.b_hp}) after {res.rounds} round(s) — final distance {res.final_distance_ft}ft"
    )


if __name__ == "__main__":
    main()

