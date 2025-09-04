#!/usr/bin/env python3
import argparse
from grimbrain.engine.types import Combatant
from grimbrain.engine.skirmish import run_skirmish
from grimbrain.character import Character


def mk(str_, dex, con, pb):
    return Character(str_score=str_, dex_score=dex, con_score=con, proficiency_bonus=pb,
                     proficiencies={"simple weapons", "martial weapons"})


def main():
    # keep it simple: hardcode a 2v2 sample; flags can be added later
    A1 = Combatant("FtrA", mk(18, 12, 14, 2), hp=24, weapon="Longsword", team="A")
    A2 = Combatant("ArcherA", mk(10, 18, 12, 2), hp=16, weapon="Shortbow", team="A")
    B1 = Combatant("FtrB", mk(18, 12, 14, 2), hp=24, weapon="Greataxe", team="B")
    B2 = Combatant("ArcherB", mk(10, 18, 12, 2), hp=16, weapon="Shortbow", team="B")

    res = run_skirmish([A1, A2, B1, B2], seed=12, start_distance_ft=20, max_rounds=8)
    print("\n".join(res["log"]))
    print(f"\nResult: winner={res['winner']}  team_hp={res['team_hp']} after {res['rounds']} rounds")


if __name__ == "__main__":
    main()

