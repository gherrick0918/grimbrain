#!/usr/bin/env python3
import argparse
import random

from grimbrain.character import Character
from grimbrain.engine.rest import long_rest, short_rest
from grimbrain.engine.types import Combatant


def mk_char(str_, dex, con, pb):
    return Character(
        str_score=str_,
        dex_score=dex,
        con_score=con,
        proficiency_bonus=pb,
        proficiencies={"simple weapons", "martial weapons"},
    )


def main():
    ap = argparse.ArgumentParser(description="Grimbrain rest demo")
    ap.add_argument("--name", default="Hero")
    ap.add_argument("--hp", type=int, required=True)
    ap.add_argument("--max-hp", type=int, default=None)
    ap.add_argument("--hd-faces", type=int, default=8)
    ap.add_argument("--hd-total", type=int, default=1)
    ap.add_argument("--hd-remaining", type=int, default=1)
    ap.add_argument("--str", type=int, default=10)
    ap.add_argument("--dex", type=int, default=10)
    ap.add_argument("--con", type=int, default=14)
    ap.add_argument("--pb", type=int, default=2)
    ap.add_argument("--short", type=int, default=0, help="spend N hit dice")
    ap.add_argument("--long", action="store_true")

    args = ap.parse_args()
    c = Combatant(
        name=args.name,
        actor=mk_char(args.str, args.dex, args.con, args.pb),
        hp=args.hp,
        weapon="Longsword",
        max_hp=args.max_hp,
        hd_faces=args.hd_faces,
        hd_total=args.hd_total,
        hd_remaining=args.hd_remaining,
    )

    if args.long:
        res = long_rest(c)
        print(
            f"Long rest: +{res['healed']} HP, HD now {res['hd_remaining']}/{args.hd_total}, HP={c.hp}"
        )
    elif args.short > 0:
        res = short_rest(c, spend=args.short, rng=random.Random(42))
        print(
            f"Short rest: spent {res['spent']} HD (d{args.hd_faces}), rolls={res['rolls']}, "
            f"healed {res['healed']}, HP={c.hp}, HD={c.hd_remaining}/{args.hd_total}"
        )
    else:
        print("No rest action given.")


if __name__ == "__main__":
    main()

