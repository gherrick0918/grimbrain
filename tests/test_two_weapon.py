from pathlib import Path

from grimbrain.codex.weapons import WeaponIndex
from grimbrain.rules.attacks import damage_string, attack_bonus


class C:
    def __init__(self, str_=16, dex=16, pb=2, styles=None):
        self.str_score = str_
        self.dex_score = dex
        self.proficiency_bonus = pb
        self.fighting_styles = styles or set()
        self.proficiencies = {"martial weapons", "simple weapons"}

    def ability_mod(self, k):
        return ({"STR": self.str_score, "DEX": self.dex_score}[k] - 10) // 2


def test_offhand_no_style_suppresses_mod():
    idx = WeaponIndex.load(Path("data/weapons.json"))
    c = C()
    w = idx.get("dagger")  # light, finesse
    # primary
    assert " +3 " in damage_string(c, w)
    # off-hand (no style)
    assert " +3 " not in damage_string(c, w, offhand=True)


def test_offhand_with_style_restores_mod():
    idx = WeaponIndex.load(Path("data/weapons.json"))
    c = C(styles={"Two-Weapon Fighting"})
    w = idx.get("handaxe")
    assert " +3 " in damage_string(c, w, offhand=True)


def test_attack_bonus_unchanged_for_offhand():
    idx = WeaponIndex.load(Path("data/weapons.json"))
    c = C()
    w = idx.get("dagger")
    ab = attack_bonus(c, w)
    assert isinstance(ab, int)

