from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class Character:
    """Minimal character model used for attack calculations."""

    str_score: int = 10
    dex_score: int = 10
    proficiencies: Set[str] = field(default_factory=set)
    proficiency_bonus: int = 2
    fighting_styles: Set[str] = field(default_factory=set)
    equipped_weapons: List[str] = field(default_factory=list)
    equipped_offhand: Optional[str] = None
    ammo: Dict[str, int] = field(default_factory=dict)

    def ability_mod(self, key: str) -> int:
        score = {"STR": self.str_score, "DEX": self.dex_score}[key]
        return (score - 10) // 2

    # Ammo helpers
    def ammo_count(self, ammo_type: str) -> int:
        return int(self.ammo.get(ammo_type, 0))

    def add_ammo(self, ammo_type: str, amount: int) -> None:
        self.ammo[ammo_type] = self.ammo_count(ammo_type) + max(0, amount)

    def spend_ammo(self, ammo_type: str, amount: int = 1) -> bool:
        have = self.ammo_count(ammo_type)
        if have < amount:
            return False
        self.ammo[ammo_type] = have - amount
        return True

    def attacks_and_spellcasting(
        self,
        weapon_index,
        *,
        target_ac: int | None = None,
        mode: str = "none",
    ) -> List[dict]:
        from .rules.attacks import build_attacks_block

        return build_attacks_block(
            self, weapon_index, target_ac=target_ac, mode=mode
        )

