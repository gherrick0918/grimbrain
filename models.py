from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List

class NamedText(BaseModel):
    name: str
    text: str


class ActionStruct(BaseModel):
    name: str
    attack_bonus: int
    type: str
    reach_or_range: str
    target: str
    hit_text: str
    damage_dice: str
    damage_type: str

class MonsterSidecar(BaseModel):
    name: str
    source: str
    ac: str
    hp: str
    speed: str
    str: int
    dex: int
    con: int
    int: int
    wis: int
    cha: int
    traits: List[NamedText]
    actions: List[NamedText]
    actions_struct: List[ActionStruct] = Field(default_factory=list)
    reactions: List[NamedText]
    provenance: List[str]

class SpellSidecar(BaseModel):
    name: str
    level: int
    school: str
    casting_time: str
    range: str
    components: str
    duration: str
    classes: List[str]
    text: str
    provenance: List[str]


class Attack(BaseModel):
    """Simple attack entry for a :class:`PC`."""

    name: str
    damage_dice: str
    type: str
    to_hit: int | None = None
    save_dc: int | None = None
    save_ability: str | None = None
    spell: SpellSidecar | None = None
    concentration: bool = False


class PC(BaseModel):
    """Player character sheet used by the combat engine."""

    name: str
    ac: int
    hp: int
    attacks: List[Attack]
