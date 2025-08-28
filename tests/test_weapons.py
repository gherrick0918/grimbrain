from pathlib import Path
from grimbrain.codex.weapons import WeaponIndex
from grimbrain.rules.attacks import attack_bonus, damage_string, choose_attack_ability


class DummyChar:
    def __init__(self, str_score=16, dex_score=14, pb=2, profs=None):
        self.str_score = str_score
        self.dex_score = dex_score
        self.proficiency_bonus = pb
        self.proficiencies = profs or set()

    def ability_mod(self, k):
        score = {"STR": self.str_score, "DEX": self.dex_score}[k]
        return (score - 10) // 2


def load_idx():
    return WeaponIndex.load(Path("data/weapons.json"))


def test_load_weapons():
    idx = load_idx()
    assert idx.get("dagger").damage == "1d4"


def test_finesse_picks_higher_mod():
    idx = load_idx()
    c = DummyChar(str_score=12, dex_score=18, profs={"rapier"})
    w = idx.get("rapier")
    assert choose_attack_ability(c, w) == "DEX"
    assert attack_bonus(c, w) == (4 + 2)


def test_ranged_uses_dex():
    idx = load_idx()
    c = DummyChar(str_score=18, dex_score=14, profs={"shortbow", "simple weapons"})
    w = idx.get("shortbow")
    assert choose_attack_ability(c, w) == "DEX"
    assert attack_bonus(c, w) == (2 + 2)
    assert damage_string(c, w) == "1d6 +2 piercing"


def test_thrown_defaults_str():
    idx = load_idx()
    c = DummyChar(str_score=16, dex_score=18, profs={"handaxe", "simple weapons"})
    w = idx.get("handaxe")
    assert choose_attack_ability(c, w) == "STR"
    assert attack_bonus(c, w) == (3 + 2)
    assert damage_string(c, w) == "1d6 +3 slashing"


def test_thrown_finesse_allows_dex():
    idx = load_idx()
    c = DummyChar(str_score=12, dex_score=18, profs={"dagger", "simple weapons"})
    w = idx.get("dagger")
    assert choose_attack_ability(c, w) == "DEX"
    assert attack_bonus(c, w) == (4 + 2)
    assert damage_string(c, w) == "1d4 +4 piercing"


def test_martial_no_proficiency():
    idx = load_idx()
    c = DummyChar(str_score=16, dex_score=14, profs={"simple weapons"})
    w = idx.get("longsword")
    assert attack_bonus(c, w) == 3
    assert damage_string(c, w) == "1d8 +3 slashing"


def test_versatile_two_handed_flag():
    idx = load_idx()
    from grimbrain.rules.attacks import damage_string as dmg, damage_die

    c = DummyChar(str_score=16, dex_score=10, profs={"longsword", "martial weapons"})
    w = idx.get("longsword")
    assert damage_die(c, w, two_handed=False) == "1d8"
    assert damage_die(c, w, two_handed=True) == "1d10"
    assert dmg(c, w, two_handed=True) == "1d10 +3 slashing"


def test_martial_finesse_no_proficiency():
    idx = load_idx()
    c = DummyChar(str_score=12, dex_score=16, profs={"simple weapons"})
    w = idx.get("rapier")
    assert choose_attack_ability(c, w) == "DEX"
    assert attack_bonus(c, w) == 3
    assert damage_string(c, w) == "1d8 +3 piercing"


def test_ranged_negative_dex_penalty():
    idx = load_idx()
    c = DummyChar(str_score=10, dex_score=8, profs=set())
    w = idx.get("shortbow")
    assert choose_attack_ability(c, w) == "DEX"
    assert attack_bonus(c, w) == -1
    assert damage_string(c, w) == "1d6 -1 piercing"
