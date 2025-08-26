from __future__ import annotations

from pydantic import BaseModel, Field, PositiveInt
from typing import List, Optional, Dict


class Abilities(BaseModel):
    str: PositiveInt
    dex: PositiveInt
    con: PositiveInt
    int: PositiveInt
    wis: PositiveInt
    cha: PositiveInt


class Item(BaseModel):
    name: str
    qty: PositiveInt | None = 1
    props: Dict[str, object] | None = None


class PlayerCharacter(BaseModel):
    name: str = Field(min_length=1)
    class_: str = Field(alias="class", min_length=1)
    subclass: Optional[str] = None
    background: Optional[str] = None
    race: Optional[str] = None
    level: PositiveInt
    proficiency_bonus: Optional[PositiveInt] = None
    abilities: Abilities
    ac: PositiveInt
    max_hp: PositiveInt
    current_hp: Optional[int] = None
    inventory: List[Item] = []
    spells: List[str] = []
    notes: Optional[str] = None

    class Config:
        populate_by_name = True


__all__ = ["PlayerCharacter", "Abilities", "Item"]

