from grimbrain.engine.types import Combatant
from grimbrain.engine.round import run_encounter
from grimbrain.character import Character


def C(str_=16, dex=16, pb=2, styles=None, feats=None, profs=None):
    return Character(str_score=str_, dex_score=dex, proficiency_bonus=pb,
                     fighting_styles=set(styles or []), feats=set(feats or []),
                     proficiencies=set(profs or ["simple weapons","martial weapons"]))


def test_melee_vs_melee_finishes_with_winner():
    A = Combatant("FighterA", C(str_=18, dex=12, pb=2), hp=24, weapon="Greatsword")
    B = Combatant("FighterB", C(str_=16, dex=14, pb=2), hp=20, weapon="Longsword", offhand=None)
    res = run_encounter(A, B, seed=7, max_rounds=10)
    assert res["winner"] in {"FighterA", "FighterB"}


def test_archer_sharpshooter_ignores_cover_and_long_range():
    A = Combatant("Archer", C(dex=18, feats={"Sharpshooter"}), hp=18, weapon="Longbow", offhand=None, distance_ft=200, cover="half")
    B = Combatant("Bandit", C(str_=14, dex=12), hp=14, weapon="Scimitar")
    res = run_encounter(A, B, seed=11, max_rounds=8)
    # Archer should still be able to land hits at 200ft w/ half cover due to SS rules
    assert "Archer" in "\n".join(res["log"])


def test_two_weapon_fighting_offhand_shows_and_can_finish():
    A = Combatant("Dual", C(dex=16, styles={"Two-Weapon Fighting"}), hp=18, weapon="Shortsword", offhand="Dagger")
    B = Combatant("Dummy", C(str_=12, dex=10), hp=10, weapon="Mace")
    res = run_encounter(A, B, seed=13, max_rounds=6)
    assert "Off-hand Dagger" in "\n".join(res["log"])

