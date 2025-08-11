from engine.dice import roll


def test_roll_fixed_seed():
    r1 = roll("2d6+1", seed=123)
    r2 = roll("2d6+1", seed=123)
    assert r1 == r2
    assert r1["detail"]["rolls"] == [1, 3]
    assert r1["total"] == 5


def test_adv_disadv():
    adv = roll("1d20+3", seed=42, adv=True)
    disadv = roll("1d20+3", seed=42, disadv=True)
    assert adv["detail"]["chosen"] == 4
    assert adv["total"] == 7
    assert disadv["detail"]["chosen"] == 1
    assert disadv["total"] == 4
