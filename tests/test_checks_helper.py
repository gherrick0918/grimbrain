from engine.checks import attack_roll, damage_roll, saving_throw


def test_attack_roll_deterministic():
    res = attack_roll(5, 15, seed=23)
    assert res["hit"] is True
    assert res["detail"]["total"] == 15


def test_damage_and_saves():
    dmg = damage_roll("1d8+3", seed=1)
    assert dmg["total"] == 6
    fail = saving_throw(15, 0, seed=23)
    assert fail["success"] is False
    success = saving_throw(15, 5, seed=16)
    assert success["success"] is True
