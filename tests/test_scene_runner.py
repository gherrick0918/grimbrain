from grimbrain.engine.types import Combatant
from grimbrain.engine.scene import run_scene
from grimbrain.character import Character


def C(str_=16, dex=16, pb=2, styles=None, feats=None, speed=30):
    return Character(
        str_score=str_,
        dex_score=dex,
        proficiency_bonus=pb,
        fighting_styles=set(styles or []),
        feats=set(feats or []),
        proficiencies={"simple weapons", "martial weapons"},
        speed_ft=speed,
        ammo={"arrows": 99},
    )


def test_melee_closes_then_hits():
    A = Combatant("Melee", C(str_=18), hp=22, weapon="Greatsword")
    B = Combatant("Archer", C(dex=14, feats={"Sharpshooter"}), hp=16, weapon="Longbow")
    res = run_scene(A, B, seed=9, max_rounds=5, start_distance_ft=40)
    log = "\n".join(res.log).lower()
    assert "moves: 40ft -> 10ft" in log or "moves: 40ft -> 30ft" in log  # first approach step
    assert "attacks with greatsword" in log  # eventually closes and swings


def test_archer_kites_out_of_melee_and_shoots():
    A = Combatant("Archer", C(dex=18, feats={"Sharpshooter"}), hp=18, weapon="Longbow")
    B = Combatant("Bandit", C(str_=16), hp=14, weapon="Scimitar")
    res = run_scene(A, B, seed=11, max_rounds=8, start_distance_ft=20)
    log = "\n".join(res.log).lower()
    assert "disengages and moves" in log or "moves: 20ft -> 30ft" in log
    assert "shoots with longbow" in log


def test_reach_10ft_allows_earlier_hits():
    A = Combatant("GlaiveUser", C(str_=16), hp=20, weapon="Glaive")
    B = Combatant("Dummy", C(str_=10), hp=12, weapon="Mace")
    res = run_scene(A, B, seed=5, max_rounds=3, start_distance_ft=15)
    # Should only need to step 5ft to be in reach and attack on round 1
    assert "GlaiveUser attacks with Glaive" in "\n".join(res.log)

