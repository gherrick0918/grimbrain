import random
from pathlib import Path

import typer

from grimbrain.character import Character
from grimbrain.engine.types import Combatant, Target
from grimbrain.engine.combat import grapple_action, shove_action, resolve_attack
from grimbrain.codex.weapons import WeaponIndex


app = typer.Typer(help="Demo: Grapple & Shove.")


@app.command()
def run(seed: int = 1337) -> None:
    rng = random.Random(seed)
    notes: list[str] = []
    widx = WeaponIndex.load(Path("data/weapons.json"))

    fighter = Combatant(
        name="Fighter",
        actor=Character(str_score=16, dex_score=12, proficiency_bonus=2, proficiencies={"simple weapons", "martial weapons"}),
        hp=22,
        weapon="Longsword",
        proficient_athletics=True,
    )
    archer = Combatant(
        name="Archer",
        actor=Character(str_score=10, dex_score=16, proficiency_bonus=2, proficiencies={"simple weapons", "martial weapons"}),
        hp=14,
        weapon="Longbow",
        proficient_acrobatics=True,
    )

    dist = 5
    grapple_action(fighter, archer, rng=rng, notes=notes)
    notes.append(f"Archer grappled? {'grappled' in archer.conditions} (by {archer.grappled_by})")
    shove_action(
        fighter,
        archer,
        choice="prone",
        rng=rng,
        distance_ft=dist,
        reach_threshold=5,
        notes=notes,
        trigger_oa_fn=lambda a, d: notes.append("[OA triggered]"),
    )
    tgt = Target(ac=14, hp=archer.hp, cover="none", distance_ft=dist, conditions=archer.conditions)
    res = resolve_attack(fighter.actor, fighter.weapon, tgt, widx, rng=rng)
    notes.extend(res["notes"])
    print("\n".join(notes))


if __name__ == "__main__":  # pragma: no cover - manual invocation
    app()

