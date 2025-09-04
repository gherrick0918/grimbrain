import random
from grimbrain.engine.types import Combatant
from grimbrain.engine.consumables import drink_potion_of_healing
from grimbrain.engine.scene import run_scene
from grimbrain.character import Character


def C(con=14):
    return Character(str_score=10, dex_score=10, con_score=con, proficiency_bonus=2,
                     proficiencies={"simple weapons","martial weapons"})


def test_potion_heals_and_consumes_one():
    h = Combatant("Hero", C(), hp=3, weapon="Mace", max_hp=12, consumables={"Potion of Healing": 2})
    out = drink_potion_of_healing(h, rng=random.Random(7))
    assert out["ok"] and out["healed"] >= 0 and h.consumables["Potion of Healing"] == 1
    assert h.hp <= 12


def test_cannot_drink_when_unconscious():
    h = Combatant("Hero", C(), hp=0, weapon="Mace", max_hp=12, consumables={"Potion of Healing": 1})
    out = drink_potion_of_healing(h, rng=random.Random(1))
    assert not out["ok"] and "unconscious" in out["reason"]


def test_ai_drinks_when_low_in_scene():
    # Archer starts low and has a potion; should drink on round 1
    A = Combatant("Archer", C(), hp=4, weapon="Longbow", max_hp=14, consumables={"Potion of Healing": 1})
    B = Combatant("Bandit", C(), hp=12, weapon="Scimitar")
    res = run_scene(A, B, seed=3, max_rounds=1, start_distance_ft=30)
    assert "drinks a Potion of Healing" in "\n".join(res.log)
