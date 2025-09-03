from pathlib import Path
from grimbrain.codex.armor import ArmorIndex
from grimbrain.rules.defense import compute_ac


class C:
    def __init__(self, str_=10, dex=14, shield=False, armor=None):
        self.str_score=str_; self.dex_score=dex
        self.equipped_shield=shield; self.equipped_armor=armor

def idx(): return ArmorIndex.load(Path("data/armor.json"))

def test_light_armor_full_dex():
    i = idx()
    c = C(dex=16, armor="Leather")  # 11 + Dex(3) = 14
    ac = compute_ac(c, i)
    assert ac["ac"] == 14
    assert "Leather 11" in ", ".join(ac["components"])
    assert "Dex +3" in ", ".join(ac["components"])

def test_medium_armor_caps_positive_dex_but_allows_negative():
    i = idx()
    c1 = C(dex=18, armor="Half Plate")  # 15 + min(+4, +2) = 17
    assert compute_ac(c1, i)["ac"] == 17
    c2 = C(dex=8, armor="Half Plate")   # 15 + (-1) = 14 (negative applies)
    assert compute_ac(c2, i)["ac"] == 14

def test_heavy_ignores_dex():
    i = idx()
    c = C(dex=8, armor="Chain Mail")  # 16 + 0 = 16, ignores -1
    ac = compute_ac(c, i)
    assert ac["ac"] == 16
    comps = ", ".join(ac["components"])
    assert "Chain Mail 16" in comps
    assert "Dex +0" in comps
    assert "stealth disadvantage" in "; ".join(ac["notes"])

def test_shield_adds_two():
    i = idx()
    c = C(dex=14, armor="Chain Shirt", shield=True)  # 13 + min(+2,+2)= +2 + shield +2 => 17
    assert compute_ac(c, i)["ac"] == 17

def test_unarmored_default():
    i = idx()
    c = C(dex=12, armor=None)  # 10 + Dex(+1) = 11
    ac = compute_ac(c, i)
    assert ac["ac"] == 11
    assert "unarmored 10" in ", ".join(ac["components"])

def test_strength_requirement_note():
    i = idx()
    c = C(str_=12, armor="Chain Mail")
    notes = "; ".join(compute_ac(c, i)["notes"]).lower()
    assert "str 13 req" in notes
