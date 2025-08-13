import random

from grimbrain.rules import (
    save_dc,
    roll_save,
    Conditions,
    derive_condition_advantage,
)


def test_save_dc_and_roll_deterministic():
    dc = save_dc(prof_bonus=3, ability_mod=2, misc=1)
    assert dc == 14

    rng = random.Random(42)
    success, total, face = roll_save(dc=dc, bonus=5, adv="normal", rng=rng)
    assert (success, total, face) == (False, 9, 4)

    rng = random.Random(42)
    success, total, face = roll_save(dc=16, bonus=15, adv="dis", rng=rng)
    assert (success, total, face) == (True, 16, 1)

    rng = random.Random(5)
    success, total, face = roll_save(dc=25, bonus=0, adv="normal", rng=rng)
    assert (success, total, face) == (False, 20, 20)


def test_condition_advantage_matrix():
    none = Conditions()
    restrained = Conditions(restrained=True)
    prone = Conditions(prone=True)
    frightened = Conditions(frightened=True)

    assert derive_condition_advantage(none, restrained, melee=True) == "adv"
    assert derive_condition_advantage(none, restrained, melee=False) == "adv"

    assert derive_condition_advantage(restrained, none, melee=True) == "dis"

    assert derive_condition_advantage(none, prone, melee=True) == "adv"
    assert derive_condition_advantage(none, prone, melee=False) == "dis"

    assert derive_condition_advantage(prone, none, melee=True) == "dis"
    assert derive_condition_advantage(frightened, none, melee=True) == "dis"

    assert derive_condition_advantage(frightened, restrained, melee=True) == "normal"
