from pathlib import Path
from grimbrain.codex.weapons import WeaponIndex
from grimbrain.rules.attacks import damage_display


class C:
    def __init__(self, str_=16, dex=12, pb=2):
        self.str_score = str_
        self.dex_score = dex
        self.proficiency_bonus = pb
        self.proficiencies = {"martial weapons", "simple weapons"}

    def ability_mod(self, k):
        return ({"STR": self.str_score, "DEX": self.dex_score}[k] - 10) // 2


def idx():
    return WeaponIndex.load(Path("data/weapons.json"))


def test_longsword_shows_both_modes():
    i = idx()
    c = C()
    w = i.get("longsword")
    disp = damage_display(c, w)
    assert "1d8 +3 slashing" in disp
    assert "(1d10 +3 slashing two-handed)" in disp


def test_quarterstaff_shows_both_modes():
    i = idx()
    c = C()
    w = i.get("quarterstaff")
    disp = damage_display(c, w)
    assert "1d6 +3 bludgeoning" in disp
    assert "(1d8 +3 bludgeoning two-handed)" in disp


def test_non_versatile_unchanged():
    i = idx()
    c = C()
    w = i.get("rapier")
    disp = damage_display(c, w)
    assert "(" not in disp  # no two-handed tail
