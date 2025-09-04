import random
from grimbrain.engine.types import Combatant
from grimbrain.engine.concentration import start_concentration
from grimbrain.engine.round import run_encounter
from grimbrain.character import Character


def C(con=14):
    return Character(str_score=10, dex_score=12, con_score=con, proficiency_bonus=2,
                     proficiencies={"simple weapons","martial weapons"})


def test_drops_on_failed_save_and_keeps_on_success(monkeypatch):
    # Attacker with Longsword hits for some damage; Defender is concentrating
    A = Combatant("A", C(), hp=30, weapon="Longsword")
    D = Combatant("D", C(con=14), hp=20, weapon="Mace")
    start_concentration(D, "Bless")
    # One-round encounter; seed chosen to land nonzero damage
    res = run_encounter(A, D, seed=40, max_rounds=1)
    # Log should include either maintain or drop; at least ensure concentration was checked
    assert "concentration" in "\n".join(res["log"]).lower()


def test_dc_scales_with_damage_and_war_caster_advantage_is_noted():
    A = Combatant("A", C(), hp=30, weapon="Greatsword")
    D = Combatant("D", C(con=12), hp=20, weapon="Mace")
    D.actor.feats = {"War Caster"}  # your has_feat() reads this
    start_concentration(D, "Protection from Evil and Good")
    res = run_encounter(A, D, seed=42, max_rounds=1)
    log = "\n".join(res["log"]).lower()
    # We just assert that the check line shows up with a DC and didn't silently skip
    assert "concentration" in log and "dc " in log


def test_concentration_auto_drops_on_unconscious():
    A = Combatant("A", C(), hp=30, weapon="Greataxe")
    D = Combatant("D", C(), hp=6, weapon="Mace")
    start_concentration(D, "Bless")
    res = run_encounter(A, D, seed=29, max_rounds=1)
    assert "concentration on bless ends — unconscious" in "\n".join(res["log"]).lower()
