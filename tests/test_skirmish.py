from grimbrain.engine.types import Combatant
from grimbrain.engine.skirmish import run_skirmish
from grimbrain.character import Character


def C(str_=16, dex=16, con=14, pb=2):
    return Character(str_score=str_, dex_score=dex, con_score=con, proficiency_bonus=pb,
                     proficiencies={"simple weapons", "martial weapons"})


def test_2v2_finishes_with_a_winner():
    a1 = Combatant("FtrA", C(str_=18), hp=24, weapon="Longsword", team="A")
    a2 = Combatant("ArcherA", C(dex=18), hp=16, weapon="Shortbow", team="A")
    b1 = Combatant("FtrB", C(str_=18), hp=24, weapon="Greataxe", team="B")
    b2 = Combatant("ArcherB", C(dex=18), hp=16, weapon="Shortbow", team="B")
    res = run_skirmish([a1, a2, b1, b2], seed=12, start_distance_ft=20, max_rounds=8)
    assert res["winner"] in {"A", "B"}


def test_oas_can_fire_from_multiple_enemies_when_kiting():
    a = Combatant("ArcherA", C(dex=18), hp=18, weapon="Longbow", team="A")
    g1 = Combatant("Guard1", C(str_=16), hp=20, weapon="Glaive", team="B")
    g2 = Combatant("Guard2", C(str_=16), hp=20, weapon="Glaive", team="B")
    res = run_skirmish([a, g1, g2], seed=8, start_distance_ft=10, max_rounds=2)
    assert "\n".join(res["log"]).lower().count("opportunity attack") >= 1
