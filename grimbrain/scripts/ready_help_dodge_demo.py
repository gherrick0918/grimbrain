import random
from pathlib import Path
import typer

from grimbrain.engine.types import Combatant, Target
from grimbrain.engine.combat import (
    take_dodge_action,
    take_help_action,
    take_ready_action,
    resolve_attack,
)
from grimbrain.character import Character
from grimbrain.codex.weapons import WeaponIndex

app = typer.Typer(help="Demo: Dodge / Help / Ready.")


def _C(str_=16, dex=16):
    return Character(
        str_score=str_,
        dex_score=dex,
        con_score=14,
        int_score=10,
        wis_score=10,
        cha_score=10,
        proficiency_bonus=2,
        proficiencies={"simple weapons", "martial weapons"},
    )


@app.command()
def run(seed: int = 404):
    rng = random.Random(seed)
    notes: list[str] = []
    idx = WeaponIndex.load(Path("data/weapons.json"))

    tank = Combatant("Tank", _C(str_=16), hp=40, weapon="Longsword", team="A")
    rogue = Combatant("Rogue", _C(dex=18), hp=22, weapon="Rapier", team="A")
    ogre = Combatant("Ogre", _C(str_=18), hp=30, weapon="Mace", team="B")

    # Tank Dodges; Ogre attacks Dodging Tank (disadvantage)
    take_dodge_action(tank, notes=notes)
    res1 = resolve_attack(
        ogre.actor,
        ogre.weapon,
        Target(ac=18, hp=tank.hp, distance_ft=5),
        idx,
        rng=rng,
        attacker_state=ogre,
        defender_state=tank,
    )
    notes.extend(res1["notes"])

    # Rogue helps Tank vs Ogre; Tank attacks with advantage
    take_help_action(rogue, tank, ogre, notes=notes)
    res2 = resolve_attack(
        tank.actor,
        tank.weapon,
        Target(ac=11, hp=ogre.hp, distance_ft=5),
        idx,
        rng=rng,
        attacker_state=tank,
        defender_state=ogre,
    )
    notes.extend(res2["notes"])

    # Ogre Readies vs Rogue entering melee (no movement simulated)
    take_ready_action(ogre, "enemy_enters_melee", target_id=rogue.id, notes=notes)

    print("\n".join(notes))


if __name__ == "__main__":
    app()
