from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, Field, PositiveInt

ABILITY_ORDER = ("str", "dex", "con", "int", "wis", "cha")

SKILLS: Tuple[str, ...] = (
    "acrobatics",
    "animal_handling",
    "arcana",
    "athletics",
    "deception",
    "history",
    "insight",
    "intimidation",
    "investigation",
    "medicine",
    "nature",
    "perception",
    "performance",
    "persuasion",
    "religion",
    "sleight_of_hand",
    "stealth",
    "survival",
)


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
    known_spells: List[str] = []       # stable storage for “you know these”
    prepared_spells: List[str] = []    # subset eligible to cast (for prepared casters)
    spell_slots: SpellSlots | None = None

    # Proficiencies
    save_proficiencies: Set[str] = set()
    skill_proficiencies: Set[str] = set()
    armor_proficiencies: Set[str] = set()
    weapon_proficiencies: Set[str] = set()
    languages: List[str] = []
    tool_proficiencies: List[str] = []
    equipped_weapons: List[str] = []

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
        return self.abilities.modifier(name.lower())

    def skill_mod(self, skill: str) -> int:
        key = {
            "athletics": "str",
            "acrobatics": "dex",
            "sleight_of_hand": "dex",
            "stealth": "dex",
            "arcana": "int",
            "history": "int",
            "investigation": "int",
            "nature": "int",
            "religion": "int",
            "animal_handling": "wis",
            "insight": "wis",
            "medicine": "wis",
            "perception": "wis",
            "survival": "wis",
            "deception": "cha",
            "intimidation": "cha",
            "performance": "cha",
            "persuasion": "cha",
        }[skill]
        mod = self.ability_mod(key)
        if skill in self.skill_proficiencies:
            mod += self.prof
        return mod

    def save_mod(self, ability: str) -> int:
        mod = self.ability_mod(ability)
        if ability in self.save_proficiencies:
            mod += self.prof
        return mod

    @property
    def initiative(self) -> int:
        return self.ability_mod("dex")

    @property
    def passive_perception(self) -> int:
        return 10 + self.skill_mod("perception")

    # --- Attacks ---
    def attacks(self, weapon_index) -> List[dict]:
        from grimbrain.rules.attacks import build_attacks_block

        return build_attacks_block(self, weapon_index)

    def attack_bonus(self, ability: str, proficient: bool) -> int:
        return self.ability_mod(ability) + (self.prof if proficient else 0)


__all__ = [
    "PlayerCharacter",
    "Abilities",
    "Item",
    "SpellSlots",
    "ABILITY_ORDER",
    "SKILLS",
]
