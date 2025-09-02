from pathlib import Path
from grimbrain.codex.weapons import WeaponIndex
from grimbrain.rules.attacks import attack_bonus, damage_string


def idx():
    return WeaponIndex.load(Path("data/weapons.json"))


class C:
    def __init__(self, str_=16, dex=16, pb=2, styles=None, offhand=None):
        self.str_score = str_
        self.dex_score = dex
        self.proficiency_bonus = pb
        self.fighting_styles = styles or set()
        self.proficiencies = {"simple weapons", "martial weapons"}
        self.equipped_weapons = []
        self.equipped_offhand = offhand

    def ability_mod(self, k):
        return ({"STR": self.str_score, "DEX": self.dex_score}[k] - 10) // 2


def test_archery_adds_to_ranged_attack_only():
    i = idx()
    c = C(styles={"Archery"})
    shortbow = i.get("shortbow")      # ranged weapon
    dagger = i.get("dagger")          # melee (thrown)
    # Shortbow: Dex + PB + Archery
    assert attack_bonus(c, shortbow) == (3 + 2 + 2)
    # Dagger (melee/ thrown) shouldn't get Archery bonus
    assert attack_bonus(c, dagger) == (3 + 2)


def test_dueling_adds_plus2_damage_one_handed_only():
    i = idx()
    c = C(styles={"Dueling"})
    longsword = i.get("longsword")  # versatile
    # One-handed line gains +2 damage
    assert damage_string(c, longsword, two_handed=False) == "1d8 +5 slashing"  # +3 STR, +2 Dueling
    # Two-handed line does not
    assert damage_string(c, longsword, two_handed=True) == "1d10 +3 slashing"


def test_dueling_disabled_if_offhand_weapon_present():
    i = idx()
    # Off-hand present blocks Dueling
    c = C(styles={"Dueling"}, offhand="Dagger")
    rapier = i.get("rapier")  # finesse melee
    # No +2 because another weapon is equipped
    # DEX 16 => +3; melee finesse picks DEX
    assert damage_string(c, rapier, two_handed=False) == "1d8 +3 piercing"
