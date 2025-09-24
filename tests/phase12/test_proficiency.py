from grimbrain.engine.characters import build_partymember
from grimbrain.engine.combat import contested_check_grapple_or_shove
from grimbrain.engine.saves import roll_save
from grimbrain.engine.util import make_combatant_from_party_member


class FixedRandom:
    def __init__(self, value: int) -> None:
        self.value = value

    def randint(self, _a: int, _b: int) -> int:
        return self.value


def test_skill_proficiency_in_contested_checks():
    attacker = build_partymember(
        "Athlete",
        "Fighter",
        {"STR": 16, "DEX": 12, "CON": 14, "INT": 10, "WIS": 10, "CHA": 8},
        weapon="Longsword",
        ranged=False,
        prof_skills=["Athletics"],
    )
    defender = build_partymember(
        "Target",
        "Fighter",
        {"STR": 12, "DEX": 12, "CON": 12, "INT": 10, "WIS": 10, "CHA": 10},
        weapon="Longsword",
        ranged=False,
    )
    cmb_attacker = make_combatant_from_party_member(attacker, team="A", cid="A1")
    cmb_defender = make_combatant_from_party_member(defender, team="B", cid="B1")

    win, log = contested_check_grapple_or_shove(cmb_attacker, cmb_defender, rng=FixedRandom(10))
    assert "+ PROF" in log
    assert win is True or win is False  # ensure the roll executed

    attacker_no_prof = build_partymember(
        "Novice",
        "Fighter",
        {"STR": 16, "DEX": 12, "CON": 14, "INT": 10, "WIS": 10, "CHA": 8},
        weapon="Longsword",
        ranged=False,
    )
    cmb_no_prof = make_combatant_from_party_member(attacker_no_prof, team="A", cid="A2")
    _, log_no_prof = contested_check_grapple_or_shove(cmb_no_prof, cmb_defender, rng=FixedRandom(10))
    assert "+ PROF" not in log_no_prof


def test_save_proficiency_applies_proficiency_bonus():
    hero = build_partymember(
        "Guard",
        "Fighter",
        {"STR": 10, "DEX": 10, "CON": 12, "INT": 10, "WIS": 10, "CHA": 10},
        weapon="Spear",
        ranged=False,
        prof_saves=["STR"],
    )
    cmb_hero = make_combatant_from_party_member(hero, team="A", cid="A3")
    ok, die, _ = roll_save(cmb_hero.actor, "STR", 12, rng=FixedRandom(10), combatant=cmb_hero)
    assert die == 10
    assert ok  # 10 + pb 2 >= 12 even with 0 STR mod

    hero_no_prof = build_partymember(
        "Citizen",
        "Fighter",
        {"STR": 10, "DEX": 10, "CON": 12, "INT": 10, "WIS": 10, "CHA": 10},
        weapon="Spear",
        ranged=False,
    )
    cmb_citizen = make_combatant_from_party_member(hero_no_prof, team="A", cid="A4")
    ok2, _, _ = roll_save(cmb_citizen.actor, "STR", 12, rng=FixedRandom(10), combatant=cmb_citizen)
    assert not ok2
