from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field, PositiveInt

ABILITY_ORDER = ("str", "dex", "con", "int", "wis", "cha")


class Abilities(BaseModel):
    str: PositiveInt
    dex: PositiveInt
    con: PositiveInt
    int: PositiveInt
    wis: PositiveInt
    cha: PositiveInt

    def modifier(self, name: str) -> int:
        v = getattr(self, name)
        return (v - 10) // 2


class Item(BaseModel):
    name: str
    qty: PositiveInt | None = 1
    props: Dict[str, object] | None = None


class SpellSlots(BaseModel):
    # 1..9 levels; 0 means none
    l1: int = 0
    l2: int = 0
    l3: int = 0
    l4: int = 0
    l5: int = 0
    l6: int = 0
    l7: int = 0
    l8: int = 0
    l9: int = 0


class PlayerCharacter(BaseModel):
    name: str = Field(min_length=1)
    class_: str = Field(alias="class", min_length=1)
    subclass: Optional[str] = None
    background: Optional[str] = None
    race: Optional[str] = None
    level: PositiveInt = 1
    proficiency_bonus: Optional[PositiveInt] = None
    abilities: Abilities
    ac: PositiveInt
    max_hp: PositiveInt
    current_hp: Optional[int] = None
    inventory: List[Item] = []
    spells: List[str] = []
    spell_slots: SpellSlots | None = None

    class Config:
        populate_by_name = True

    # --- Derived ---
    @property
    def prof(self) -> int:
        if self.proficiency_bonus:
            return self.proficiency_bonus
        # 5e scaling: 1–4:+2, 5–8:+3, 9–12:+4, 13–16:+5, 17–20:+6
        lvl = self.level
        return 2 + ((lvl - 1) // 4)

    def ability_mod(self, name: str) -> int:
        return self.abilities.modifier(name)


__all__ = ["PlayerCharacter", "Abilities", "Item", "SpellSlots", "ABILITY_ORDER"]
