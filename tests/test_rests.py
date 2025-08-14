import random
import pytest

from grimbrain.engine import rests
from grimbrain.models import PC


def test_multi_die_spend_and_heal():
    pc = PC(
        name="Hero",
        ac=10,
        hp=5,
        max_hp=15,
        con_mod=1,
        attacks=[],
        hit_die_size=8,
        hit_dice_max=5,
        hit_dice=5,
    )
    rng = random.Random(1)
    res = rests.apply_short_rest([pc], rng, {"Hero": 2})
    info = res["Hero"]
    assert info["spent"] == 2
    assert len(info["rolls"]) == 2
    expected = sum(max(0, r + pc.con_mod) for r in info["rolls"])
    assert info["healed"] == expected
    assert pc.hit_dice == 3


def test_over_spend_clamped():
    pc = PC(
        name="Hero",
        ac=10,
        hp=5,
        max_hp=15,
        con_mod=0,
        attacks=[],
        hit_die_size=8,
        hit_dice_max=1,
        hit_dice=1,
    )
    rng = random.Random(2)
    res = rests.apply_short_rest([pc], rng, {"Hero": 3})
    info = res["Hero"]
    assert info["spent"] == 1
    assert len(info["rolls"]) == 1
    assert pc.hit_dice == 0


def test_long_rest_recovers_hit_dice():
    pc = PC(
        name="Hero",
        ac=10,
        hp=2,
        max_hp=10,
        con_mod=0,
        attacks=[],
        hit_die_size=8,
        hit_dice_max=5,
        hit_dice=1,
    )
    res = rests.apply_long_rest([pc])
    info = res["Hero"]
    assert info["healed"] == 8
    assert info["hd_regained"] == 2
    assert pc.hit_dice == 3
    assert pc.hp == pc.max_hp


def test_reject_dead_or_in_combat():
    rng = random.Random(3)
    dead = PC(name="Dead", ac=10, hp=0, max_hp=10, attacks=[], hit_dice_max=2, hit_dice=2)
    with pytest.raises(ValueError):
        rests.apply_short_rest([dead], rng)
    with pytest.raises(ValueError):
        rests.apply_long_rest([dead])

    fighter = PC(name="Fighter", ac=10, hp=5, max_hp=10, attacks=[], hit_dice_max=2, hit_dice=2)
    object.__setattr__(fighter, "in_combat", True)
    with pytest.raises(ValueError):
        rests.apply_short_rest([fighter], rng)
    with pytest.raises(ValueError):
        rests.apply_long_rest([fighter])

