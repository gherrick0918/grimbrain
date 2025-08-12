from grimbrain.rules import mod, prof_bonus, ability_mods_from_scores

def test_mod_table():
    assert mod(8) == -1
    assert mod(10) == 0
    assert mod(15) == 2
    assert mod(18) == 4

def test_prof_bonus_table():
    assert prof_bonus(1) == 2
    assert prof_bonus(5) == 3
    assert prof_bonus(9) == 4
    assert prof_bonus(13) == 5
    assert prof_bonus(17) == 6

def test_ability_mods_from_scores():
    scores = {"STR": 14, "DEX": 12, "CON": 10, "INT": 8, "WIS": 16, "CHA": 9}
    mods = ability_mods_from_scores(scores)
    assert mods == {"STR": 2, "DEX": 1, "CON": 0, "INT": -1, "WIS": 3, "CHA": -1}
