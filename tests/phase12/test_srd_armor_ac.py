from grimbrain.engine.characters import build_partymember


def test_ac_no_armor_uses_dex():
    pm = build_partymember(
        "A",
        "Fighter",
        {"STR": 10, "DEX": 14, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10},
        weapon="Longsword",
        ranged=False,
    )
    assert pm.ac == 12
    assert pm.armor is None
    assert pm.shield is False


def test_ac_with_leather_and_shield():
    pm = build_partymember(
        "B",
        "Fighter",
        {"STR": 10, "DEX": 14, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10},
        weapon="Longsword",
        ranged=False,
        armor="Leather",
        shield=True,
    )
    assert pm.ac == 15
    assert pm.stealth_disadv is False
    assert pm.armor == "Leather"
    assert pm.shield is True


def test_ac_with_scale_mail_dex_cap_and_disadv():
    pm = build_partymember(
        "C",
        "Fighter",
        {"STR": 10, "DEX": 18, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10},
        weapon="Longsword",
        ranged=False,
        armor="Scale Mail",
    )
    assert pm.ac == 16
    assert pm.stealth_disadv is True
