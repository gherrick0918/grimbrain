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
    level: int | None = None
    concentration: bool = False


class PC(BaseModel):
    """Player character sheet used by the combat engine."""

    name: str
    ac: int
    hp: int
    attacks: List[Attack]
    max_hp: int | None = None
    con_mod: int = 0
    # Hit Dice tracking for rests
    hit_die: str = "d8"
    hit_dice_total: int = 1
    hit_dice_remaining: int | None = None
    # Spell slots by level (remaining) and their totals
    spell_slots: Dict[int, int] = Field(default_factory=dict)
    spell_slots_total: Dict[int, int] = Field(default_factory=dict)
    # Basic spellcasting stats for on-the-fly DC/attack calculations
    prof_bonus: int = 2
    spell_mod: int = 0

    def __init__(self, **data):  # type: ignore[override]
        if data.get("max_hp") is None and "hp" in data:
            data["max_hp"] = data.get("hp")
        if data.get("con_mod") is None:
            data["con_mod"] = 0
        # Back-compat: allow old field names
        if "hit_die_size" in data and "hit_die" not in data:
            data["hit_die"] = f"d{data.pop('hit_die_size')}"
        if "hit_dice_max" in data and "hit_dice_total" not in data:
            data["hit_dice_total"] = data.pop("hit_dice_max")
        if "hit_dice" in data and "hit_dice_remaining" not in data:
            data["hit_dice_remaining"] = data.pop("hit_dice")

        if data.get("hit_dice_total") is None:
            data["hit_dice_total"] = data.get("hit_dice_remaining", 1)
        if data.get("hit_dice_remaining") is None:
            data["hit_dice_remaining"] = data.get("hit_dice_total", 1)
        if data.get("hit_die") is None:
            data["hit_die"] = "d8"

        # Spell slots: if only one of total/remaining provided, mirror it
        slots = data.get("spell_slots")
        slots_total = data.get("spell_slots_total")
        if slots_total is None and slots is not None:
            data["spell_slots_total"] = slots.copy()
        elif slots is None and slots_total is not None:
            data["spell_slots"] = slots_total.copy()
        super().__init__(**data)


def dump_model(m: BaseModel) -> Dict[str, Any]:
    """Return a ``dict`` for a Pydantic model across v1/v2."""
    if hasattr(m, "model_dump"):
        return m.model_dump()
    return m.dict()
