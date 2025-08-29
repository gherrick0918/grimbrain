from pathlib import Path
from grimbrain.codex.weapons import WeaponIndex, Weapon
from grimbrain.rules.attacks import damage_string, crit_damage_string
from grimbrain.rules.attack_math import hit_probabilities


class C:
    def __init__(self, str_=16, dex=18, pb=2, styles=None):
        self.str_score = str_
        self.dex_score = dex
        self.proficiency_bonus = pb
        self.fighting_styles = styles or set()
        self.proficiencies = {"simple weapons", "martial weapons"}

    def ability_mod(self, k):
        return ({"STR": self.str_score, "DEX": self.dex_score}[k] - 10) // 2


def idx():
    return WeaponIndex.load(Path("data/weapons.json"))


def test_crit_damage_doubles_only_dice():
    i = idx()
    c = C()
    # Greatsword 2d6 -> 4d6 +3
    w = i.get("greatsword")
    assert damage_string(c, w) == "2d6 +3 slashing"
    assert crit_damage_string(c, w) == "4d6 +3 slashing"
    # Rapier 1d8 -> 2d8 +4 (DEX)
    r = i.get("rapier")
    assert "1d8 +4 piercing" == damage_string(c, r)
    assert "2d8 +4 piercing" == crit_damage_string(c, r)
    # Blowgun "1" stays "1"
    b = i.get("blowgun")
    assert "1 +4 piercing" == damage_string(c, b)
    assert "1 +4 piercing" == crit_damage_string(c, b)
    # Net "—"
    n = Weapon(
        name="net",
        category="martial",
        kind="ranged",
        damage="—",
        damage_type="special",
        properties=[],
    )
    assert "— special" == crit_damage_string(c, n)


def test_offhand_crit_suppresses_mod_without_style():
    i = idx()
    c = C(styles=set())  # no Two-Weapon Fighting
    d = i.get("dagger")
    # Off-hand has no ability mod; crit doubles dice only
    assert crit_damage_string(c, d, offhand=True) == "2d4 piercing"


def test_hit_probabilities_basic_and_extremes():
    # +5 vs AC 15 -> need 10; single: 50% noncrit + 5% crit = 55%
    p = hit_probabilities(attack_bonus=5, ac=15, mode="none")
    assert abs(p["hit"] - 0.55) < 1e-9
    assert abs(p["crit"] - 0.05) < 1e-9
    # Very high AC (only nat20s land): none=5%, adv≈9.75%, dis=0.25%
    p_hi = hit_probabilities(attack_bonus=0, ac=30, mode="none")
    p_hi_adv = hit_probabilities(0, 30, "advantage")
    p_hi_dis = hit_probabilities(0, 30, "disadvantage")
    assert abs(p_hi["hit"] - 0.05) < 1e-9
    assert abs(p_hi_adv["hit"] - 0.0975) < 1e-9
    assert abs(p_hi_dis["hit"] - 0.0025) < 1e-9
    # Monotonic sanity: adv > none > dis
    p_mid = [hit_probabilities(5, 16, m)["hit"] for m in ("disadvantage", "none", "advantage")]
    assert p_mid[0] < p_mid[1] < p_mid[2]
