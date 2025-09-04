#!/usr/bin/env python3
import argparse, random
from grimbrain.engine.types import Combatant
from grimbrain.engine.consumables import drink_potion_of_healing
from grimbrain.character import Character

def main():
    ap = argparse.ArgumentParser(description="Drink a Potion of Healing")
    ap.add_argument("--name", default="Hero")
    ap.add_argument("--hp", type=int, required=True)
    ap.add_argument("--max-hp", type=int, required=True)
    ap.add_argument("--count", type=int, default=1)
    args = ap.parse_args()

    c = Combatant(name=args.name,
                  actor=Character(str_score=10, dex_score=10, con_score=14, proficiency_bonus=2,
                                  proficiencies={"simple weapons","martial weapons"}),
                  hp=args.hp, weapon="Mace", max_hp=args.max_hp,
                  consumables={"Potion of Healing": args.count})
    res = drink_potion_of_healing(c, rng=random.Random(1))
    if res["ok"]:
        print(f"{c.name} drinks a Potion of Healing: rolls={res['rolls']} total={res['total']} → healed {res['healed']}; HP={c.hp}; remaining={res['remaining']}")
    else:
        print(f"Failed: {res['reason']}")

if __name__ == "__main__":
    main()
