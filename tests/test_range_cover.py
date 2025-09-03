from pathlib import Path

from grimbrain.codex.weapons import WeaponIndex
from grimbrain.rules.attacks import build_attacks_block


class C:
    def __init__(self, str_=16, dex=18, pb=2, feats=None):
        self.str_score = str_
        self.dex_score = dex
        self.proficiency_bonus = pb
        self.proficiencies = {"simple weapons", "martial weapons"}
        self.fighting_styles = set()
        self.feats = set(feats or [])
        self.equipped_weapons = ["Longbow", "Dagger"]
        self.equipped_offhand = None

    def ability_mod(self, k):
        return ({"STR": self.str_score, "DEX": self.dex_score}[k] - 10) // 2

    def ammo_count(self, _):
        return 0


def idx():
    return WeaponIndex.load(Path("data/weapons.json"))


def _odds_of(name, block):
    return next(e["odds"] for e in block if e["name"].lower() == name.lower())


def test_long_range_imposes_disadvantage_without_ss():
    i = idx()
    c = C(feats=set())
    b1 = build_attacks_block(
        c, i, target_ac=15, target_distance=200, cover="none", mode="none"
    )
    b0 = build_attacks_block(
        c, i, target_ac=15, target_distance=100, cover="none", mode="none"
    )
    o1 = _odds_of("Longbow", b1)
    o0 = _odds_of("Longbow", b0)
    assert "long range" in o1.lower()
    hit1 = float(o1.split("hit ")[1].split("%")[0])
    hit0 = float(o0.split("hit ")[1].split("%")[0])
    assert hit1 < hit0


def test_sharpshooter_cancels_long_range_disadvantage():
    i = idx()
    c = C(feats={"Sharpshooter"})
    b = build_attacks_block(
        c, i, target_ac=15, target_distance=200, cover="none", mode="none"
    )
    o = _odds_of("Longbow", b)
    assert "no disadvantage" in o.lower()


def test_cover_adds_to_ac_unless_ss_ignores():
    i = idx()
    c = C()
    b_cov = build_attacks_block(c, i, target_ac=15, cover="half", mode="none")
    b_none = build_attacks_block(c, i, target_ac=15, cover="none", mode="none")
    oc = _odds_of("Longbow", b_cov)
    on = _odds_of("Longbow", b_none)
    hc = float(oc.split("vs AC ")[1].split()[0])
    hn = float(on.split("vs AC ")[1].split()[0])
    assert hc == hn + 2

    c_ss = C(feats={"Sharpshooter"})
    b_ss = build_attacks_block(c_ss, i, target_ac=15, cover="three-quarters")
    o_ss = _odds_of("Longbow", b_ss)
    assert "ignore cover" in o_ss.lower()
    ac_ss = float(o_ss.split("vs AC ")[1].split()[0])
    assert ac_ss == 15


def test_out_of_range_and_total_cover_unattackable():
    i = idx()
    c = C()
    b1 = build_attacks_block(c, i, target_ac=15, target_distance=1000, cover="none")
    assert "unattackable" in _odds_of("Longbow", b1).lower()
    b2 = build_attacks_block(c, i, target_ac=15, cover="total")
    assert "unattackable" in _odds_of("Longbow", b2).lower()


def test_thrown_weapons_use_range_profile():
    i = idx()
    c = C()
    b = build_attacks_block(c, i, target_ac=15, target_distance=50, cover="none")
    o = _odds_of("Dagger", b)
    assert "long range" in o.lower()

