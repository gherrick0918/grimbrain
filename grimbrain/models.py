from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any, Dict, List

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
    max_hp: int | None = None
    con_mod: int = 0
    hit_die_size: int = 8
    hit_dice_max: int = 1
    hit_dice: int | None = None

    def __init__(self, **data):  # type: ignore[override]
        if data.get("max_hp") is None and "hp" in data:
            data["max_hp"] = data.get("hp")
        if data.get("con_mod") is None:
            data["con_mod"] = 0
        if data.get("hit_dice_max") is None:
            data["hit_dice_max"] = data.get("hit_dice", 1)
        if data.get("hit_dice") is None:
            data["hit_dice"] = data.get("hit_dice_max", 1)
        if data.get("hit_die_size") is None:
            data["hit_die_size"] = 8
        super().__init__(**data)


def dump_model(m: BaseModel) -> Dict[str, Any]:
    """Return a ``dict`` for a Pydantic model across v1/v2."""
    if hasattr(m, "model_dump"):
        return m.model_dump()
    return m.dict()
