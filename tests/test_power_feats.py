from pathlib import Path
from grimbrain.codex.weapons import WeaponIndex
from grimbrain.rules.attacks import attack_bonus, damage_string, build_attacks_block


def idx():
    return WeaponIndex.load(Path("data/weapons.json"))


class C:
    def __init__(self, str_=16, dex=16, pb=2, feats=None):
        self.str_score = str_
        self.dex_score = dex
        self.proficiency_bonus = pb
        self.proficiencies = {"simple weapons", "martial weapons"}
        self.fighting_styles = set()
        self.feats = set(feats or [])
        self.equipped_weapons = []
        self.equipped_offhand = None
        self.ammo = {}

    def ability_mod(self, k):
        return ({"STR": self.str_score, "DEX": self.dex_score}[k] - 10) // 2

    def ammo_count(self, ammo_type):
        return int(self.ammo.get(ammo_type, 0))


def test_sharpshooter_power_variant_math():
    i = idx()
    c = C(dex=18, feats={"Sharpshooter"})
    bow = i.get("longbow")  # ranged
    # base AB: +4(Dex) +2(PB) = +6; power -> +1
    assert attack_bonus(c, bow) == 6
    assert attack_bonus(c, bow, power=True) == 1
    # dmg base: 1d8 +4; power adds +10
    assert damage_string(c, bow) == "1d8 +4 piercing"
    assert damage_string(c, bow, power=True) == "1d8 +14 piercing"


def test_gwm_power_variant_math():
    i = idx()
    c = C(str_=18, feats={"Great Weapon Master"})
    gs = i.get("greatsword")  # heavy melee
    # base AB: +4(STR)+2(PB)=+6; power -> +1
    assert attack_bonus(c, gs) == 6
    assert attack_bonus(c, gs, power=True) == 1
    # dmg base: 2d6 +4; power adds +10
    assert damage_string(c, gs) == "2d6 +4 slashing"
    assert damage_string(c, gs, power=True) == "2d6 +14 slashing"


def test_power_lines_appear_only_when_eligible():
    i = idx()
    c = C(feats={"Sharpshooter"})
    c.equipped_weapons = ["Dagger", "Longbow"]  # dagger not eligible; longbow eligible
    block = build_attacks_block(c, i, target_ac=15, show_power_variant=True)
    names = [e["name"].lower() for e in block]
    assert "longbow (ss -5/+10)" in names
    assert not any("dagger (ss -5/+10)" in n for n in names)
    # and odds should be included because target_ac was provided
    power_entry = next(e for e in block if "(ss -5/+10)" in e["name"].lower())
    assert "hit " in power_entry.get("odds", "") and "crit " in power_entry.get("odds", "")


def test_no_power_line_without_feat():
    i = idx()
    c = C()  # no feats
    c.equipped_weapons = ["Longbow", "Greatsword"]
    block = build_attacks_block(c, i, show_power_variant=True)
    assert all("(ss -5/+10)" not in e["name"].lower() and "(gwm -5/+10)" not in e["name"].lower() for e in block)
