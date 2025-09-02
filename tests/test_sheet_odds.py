from pathlib import Path

from grimbrain.codex.weapons import WeaponIndex
from grimbrain.rules.attacks import build_attacks_block


class C:
    def __init__(self):
        self.str_score = 16
        self.dex_score = 14
        self.proficiency_bonus = 2
        self.proficiencies = {"simple weapons", "martial weapons"}
        self.equipped_weapons = ["Longsword"]

    def ability_mod(self, k):
        return ({"STR": self.str_score, "DEX": self.dex_score}[k] - 10) // 2


def test_odds_string_present_and_sane():
    i = WeaponIndex.load(Path("data/weapons.json"))
    c = C()
    block = build_attacks_block(c, i, target_ac=15, mode="none")
    odds = block[0]["odds"]
    assert "hit 55.0%" in odds and "crit 5.0%" in odds and "vs AC 15" in odds

