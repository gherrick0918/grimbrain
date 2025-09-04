import random

from grimbrain.character import Character
from grimbrain.engine.rest import long_rest, short_rest
from grimbrain.engine.types import Combatant


def C(con=14):
    return Character(
        str_score=10,
        dex_score=12,
        con_score=con,
        proficiency_bonus=2,
        proficiencies={"simple weapons", "martial weapons"},
    )


def test_short_rest_spends_dice_and_caps_to_max_hp():
    cmb = Combatant(
        "Hero",
        C(con=14),
        hp=5,
        weapon="Mace",
        max_hp=12,
        hd_faces=8,
        hd_total=3,
        hd_remaining=3,
    )
    res = short_rest(cmb, spend=2, rng=random.Random(1))
    assert 0 < res["healed"] <= 7  # can’t exceed the gap to max
    assert cmb.hd_remaining == 3 - res["spent"]


def test_short_rest_no_dice_left_heals_zero():
    cmb = Combatant(
        "Dry",
        C(),
        hp=5,
        weapon="Mace",
        max_hp=12,
        hd_faces=8,
        hd_total=1,
        hd_remaining=0,
    )
    res = short_rest(cmb, spend=2, rng=random.Random(1))
    assert res["healed"] == 0 and res["spent"] == 0


def test_long_rest_full_heal_and_regain_half_dice_drop_temp_hp_and_clear_conditions():
    cmb = Combatant(
        "Tired",
        C(),
        hp=3,
        weapon="Mace",
        max_hp=15,
        hd_faces=10,
        hd_total=5,
        hd_remaining=1,
        temp_hp=4,
        conditions={"poisoned", "restrained"},
    )
    out = long_rest(cmb)
    assert cmb.hp == 15 and cmb.temp_hp == 0
    assert cmb.hd_remaining == 1 + (5 // 2)  # +2 regained, capped by total
    assert "poisoned" not in cmb.conditions and "restrained" not in cmb.conditions

