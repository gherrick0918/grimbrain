import random
from grimbrain.rules import (
    ArmorProfile,
    ac_calc,
    resolve_attack_ability,
    attack_bonus,
    initiative_bonus,
    roll_attack,
    roll_damage,
)

def test_ac_calc_light_medium_heavy():
    dex_mod = 3
    # Light (e.g., Leather 11 + Dex)
    ac_light = ac_calc(ArmorProfile(base=11, kind="light"), dex_mod, shield_bonus=0)
    assert ac_light == 14

    # Medium (e.g., Chain Shirt 14 + Dex (max 2))
    ac_medium = ac_calc(ArmorProfile(base=14, kind="medium", dex_cap=2), dex_mod, shield_bonus=0)
    assert ac_medium == 16

    # Heavy (e.g., Chain Mail 16 + Shield 2, Dex ignored)
    ac_heavy = ac_calc(ArmorProfile(base=16, kind="heavy", dex_cap=0), dex_mod, shield_bonus=2)
    assert ac_heavy == 18

def test_attack_math_and_initiative():
    # Finesse weapon -> DEX
    weapon = {"type": "melee", "finesse": True, "ranged": False}
    assert resolve_attack_ability(weapon) == "DEX"

    # Attack bonus: ability + prof(level) + misc
    to_hit = attack_bonus(ability_mod=3, proficient=True, level=5, misc=1)
    assert to_hit == 7  # 3 + prof(5)=3 + 1

    # Initiative bonus
    assert initiative_bonus(dex_mod=3, misc=1) == 4

def test_roll_attack_advantage_and_disadvantage_are_deterministic_with_seed():
    rng = random.Random(42)
    total, is_crit, is_n1, face = roll_attack(to_hit=5, adv="normal", rng=rng)
    assert (total, is_crit, is_n1, face) == (9, False, False, 4)

    rng = random.Random(42)
    total, is_crit, is_n1, face = roll_attack(to_hit=5, adv="adv", rng=rng)
    assert (total, is_crit, is_n1, face) == (9, False, False, 4)

    rng = random.Random(42)
    total, is_crit, is_n1, face = roll_attack(to_hit=5, adv="dis", rng=rng)
    assert (total, is_crit, is_n1, face) == (6, False, True, 1)

def test_roll_damage_and_crit_doubles_dice_only():
    # Deterministic roller for unit tests
    fixed = {"1d8": 5, "2d6": 7}
    def roller(expr: str) -> int:
        return fixed[expr]

    # Normal hit: 1d8 + 3 == 5 + 3
    assert roll_damage("1d8", mod_val=3, crit=False, roller=roller) == 8

    # Crit: doubles dice only: (1d8 + 1d8) + 3 == 5 + 5 + 3
    assert roll_damage("1d8", mod_val=3, crit=True, roller=roller) == 13
