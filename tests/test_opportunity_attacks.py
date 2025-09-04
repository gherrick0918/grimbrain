from grimbrain.engine.types import Combatant
from grimbrain.engine.scene import run_scene
from grimbrain.character import Character


def C(str_=16, dex=16, con=14, pb=2):
    return Character(
        str_score=str_,
        dex_score=dex,
        proficiency_bonus=pb,
        fighting_styles=set(),
        feats=set(),
        proficiencies={"simple weapons", "martial weapons"},
        speed_ft=30,
        ammo={},
        con_score=con,
    )


def test_leaving_reach_without_disengage_triggers_oa():
    # Defender has reach (Glaive 10 ft). Attacker starts at 10 ft and kites -> should provoke OA.
    A = Combatant("Archer", C(dex=18), hp=14, weapon="Longbow")
    G = Combatant("Guardian", C(str_=16), hp=20, weapon="Glaive")
    res = run_scene(A, G, seed=8, max_rounds=1, start_distance_ft=10)
    assert "opportunity attack" in "\n".join(res.log).lower()


def test_disengage_prevents_oa_at_5ft():
    # At 5 ft, ranged will Disengage then move; no OA should fire.
    A = Combatant("Archer", C(dex=18), hp=14, weapon="Longbow")
    S = Combatant("Swordsman", C(str_=16), hp=20, weapon="Longsword")
    res = run_scene(A, S, seed=9, max_rounds=1, start_distance_ft=5)
    assert "opportunity attack" not in "\n".join(res.log).lower()
