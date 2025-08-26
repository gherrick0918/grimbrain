from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from grimbrain.models.pc import Abilities, PlayerCharacter, SpellSlots

# Simple SRD baseline hit-die map
HIT_DIE = {
    "Barbarian": 12,
    "Fighter": 10,
    "Paladin": 10,
    "Ranger": 10,
    "Bard": 8,
    "Cleric": 8,
    "Druid": 8,
    "Monk": 8,
    "Rogue": 8,
    "Warlock": 8,
    "Sorcerer": 6,
    "Wizard": 6,
}

# Wizard slots quick table (L1–L5 for example). Extend for full SRD later.
WIZARD_SLOTS = {
    1: (2, 0, 0, 0, 0, 0, 0, 0, 0),
    2: (3, 0, 0, 0, 0, 0, 0, 0, 0),
    3: (4, 2, 0, 0, 0, 0, 0, 0, 0),
    4: (4, 3, 0, 0, 0, 0, 0, 0, 0),
    5: (4, 3, 2, 0, 0, 0, 0, 0, 0),
}


@dataclass
class PCOptions:
    name: str
    klass: str  # e.g., 'Wizard'
    race: str | None
    background: str | None
    abilities: dict  # {str,dex,con,int,wis,cha}
    ac: int


# --- Creation ---


def create_pc(opts: PCOptions) -> PlayerCharacter:
    abilities = Abilities(**opts.abilities)
    hd = HIT_DIE.get(opts.klass, 8)
    con_mod = abilities.modifier("con")
    max_hp = hd + con_mod  # L1 max per 5e baseline
    pc = PlayerCharacter(
        name=opts.name,
        **{"class": opts.klass},
        race=opts.race,
        background=opts.background,
        level=1,
        abilities=abilities,
        ac=opts.ac,
        max_hp=max_hp,
        current_hp=max_hp,
        spell_slots=_spell_slots_for(opts.klass, 1),
    )
    return pc


# --- Leveling ---


def level_up(pc: PlayerCharacter, new_level: int) -> PlayerCharacter:
    if new_level <= pc.level:
        return pc
    klass = pc.class_
    hd = HIT_DIE.get(klass, 8)
    con_mod = pc.ability_mod("con")
    # Average HP per 5e (rounded up): d6=4, d8=5, d10=6, d12=7
    avg = {6: 4, 8: 5, 10: 6, 12: 7}[hd]
    gained = (new_level - pc.level) * (avg + con_mod)
    pc.level = new_level
    pc.max_hp += max(1, gained)
    pc.current_hp = pc.max_hp
    pc.spell_slots = _spell_slots_for(klass, new_level)
    return pc


# --- Inventory ---


def add_item(pc: PlayerCharacter, name: str, qty: int = 1, **props) -> None:
    for it in pc.inventory:
        if it.name == name:
            it.qty = (it.qty or 0) + qty
            if props:
                it.props = {**(it.props or {}), **props}
            return
    from grimbrain.models.pc import Item

    pc.inventory.append(Item(name=name, qty=qty, props=props or None))


# --- Spells ---


def learn_spell(pc: PlayerCharacter, spell_name: str) -> None:
    if spell_name not in pc.spells:
        pc.spells.append(spell_name)


# --- Slots helper ---


def _spell_slots_for(klass: str, lvl: int) -> SpellSlots | None:
    if klass == "Wizard":
        t = WIZARD_SLOTS.get(lvl)
        if t:
            return SpellSlots(
                l1=t[0],
                l2=t[1],
                l3=t[2],
                l4=t[3],
                l5=t[4],
                l6=t[5],
                l7=t[6],
                l8=t[7],
                l9=t[8],
            )
    return None


# --- IO ---


def save_pc(pc: PlayerCharacter, path: Path) -> None:
    data = pc.model_dump(by_alias=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
