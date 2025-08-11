from grimbrain.engine.combat import run_encounter
from tests.test_combat_round import make_goblin
from grimbrain.models import SpellSidecar, Attack, PC

fireball = SpellSidecar(
    name="Fireball",
    level=3,
    school="Evocation",
    casting_time="1 action",
    range="150 feet",
    components="V,S,M",
    duration="Instantaneous",
    classes=["Wizard"],
    text="A bright streak flares.",
    provenance=["PHB"],
)

caster = PC(
    name="Mage",
    ac=12,
    hp=20,
    attacks=[Attack(name="Fireball", damage_dice="8d6", type="spell", save_dc=13, save_ability="dex", spell=fireball)],
)


def test_fireball_saves_and_damage():
    goblins = [make_goblin(), make_goblin(), make_goblin()]
    res = run_encounter([caster], goblins, seed=1, max_rounds=1)
    mons = res["state"]["monsters"]
    losses = [7 - m["hp"] for m in mons]
    assert losses == [28, 28, 14]
