from grimbrain.engine.types import Combatant
from grimbrain.engine.round import run_encounter
from grimbrain.engine.scene import run_scene
from grimbrain.character import Character


def CF(swings):
    c = Character(str_score=18, dex_score=12, proficiency_bonus=2)
    c.attacks_per_action = swings
    return c


def test_round_runner_two_swings():
    A = Combatant("Ftr", CF(2), hp=30, weapon="Longsword")
    B = Combatant("Dummy", Character(str_score=10, dex_score=10, proficiency_bonus=2), hp=20, weapon="Mace")
    res = run_encounter(A, B, seed=21, max_rounds=1)
    assert res["b_hp"] < 20


def test_loading_limits_to_one_per_action():
    c = CF(2)
    c.add_ammo("bolts", 1)
    A = Combatant("Xbow", c, hp=18, weapon="Light Crossbow")
    B = Combatant("Target", Character(str_score=10, dex_score=10, proficiency_bonus=2), hp=18, weapon="Mace")
    res = run_scene(A, B, seed=23, max_rounds=1, start_distance_ft=30)
    assert "\n".join(res.log).lower().count("light crossbow") == 1
