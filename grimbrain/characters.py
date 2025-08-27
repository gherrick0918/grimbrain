from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from grimbrain.models.pc import Abilities, PlayerCharacter, SpellSlots
from grimbrain.rules_equipment import (
    BACKGROUND_KITS,
    BACKGROUND_LANGUAGES,
    BACKGROUND_TOOLS,
    CLASS_KITS,
    KitItem,
)
from grimbrain.rules_core import (
    BACKGROUND_SKILLS,
    CLASS_SAVE_PROFS,
    FULL_CASTER_SLOTS,
    PACT_MAGIC,
    HALF_CASTERS,
    is_third_caster,
    half_caster_level,
    third_caster_level,
)

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

@dataclass
class PCOptions:
    name: str
    klass: str  # e.g., 'Wizard'
    race: str | None
    background: str | None
    abilities: dict  # {str,dex,con,int,wis,cha}
    ac: int
    subclass: str | None = None


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
        subclass=opts.subclass,
        level=1,
        abilities=abilities,
        ac=opts.ac,
        max_hp=max_hp,
        current_hp=max_hp,
        spell_slots=_spell_slots_for(opts.klass, 1, opts.subclass),
    )
    pc.save_proficiencies = CLASS_SAVE_PROFS.get(opts.klass, set())
    if opts.background:
        pc.skill_proficiencies = BACKGROUND_SKILLS.get(opts.background, set())
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
    pc.spell_slots = _spell_slots_for(klass, new_level, pc.subclass)
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


def apply_items(pc: PlayerCharacter, kit: list[KitItem]) -> None:
    for it in kit:
        add_item(pc, it.name, it.qty, **(it.props or {}))


def apply_starter_kits(pc: PlayerCharacter) -> None:
    kit = CLASS_KITS.get(pc.class_, [])
    apply_items(pc, kit)
    if pc.background:
        apply_items(pc, BACKGROUND_KITS.get(pc.background, []))
        langs = BACKGROUND_LANGUAGES.get(pc.background, [])
        for l in langs:
            if l not in pc.languages:
                pc.languages.append(l)
        tools = BACKGROUND_TOOLS.get(pc.background, [])
        for t in tools:
            if t not in pc.tool_proficiencies:
                pc.tool_proficiencies.append(t)


# --- Spells ---


def learn_spell(pc: PlayerCharacter, spell_name: str) -> None:
    if spell_name not in pc.spells:
        pc.spells.append(spell_name)


# --- Slots helper ---


def _spell_slots_for(
    klass: str, lvl: int, subclass: str | None = None
) -> SpellSlots | None:
    # Full casters
    if klass in {"Bard", "Cleric", "Druid", "Sorcerer", "Wizard"}:
        t = FULL_CASTER_SLOTS.get(lvl)
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

    # Pact magic: Warlock
    if klass == "Warlock":
        slots, slot_level = PACT_MAGIC[lvl]
        sp = SpellSlots()
        setattr(sp, f"l{slot_level}", slots)
        return sp

    # Half-casters
    if klass in HALF_CASTERS:
        cl = half_caster_level(lvl)
        t = FULL_CASTER_SLOTS.get(cl)
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

    # Third-casters
    if is_third_caster(klass, subclass):
        cl = third_caster_level(lvl)
        t = FULL_CASTER_SLOTS.get(cl)
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

    # Non-casters
    return None


# --- IO ---


def save_pc(pc: PlayerCharacter, path: Path) -> None:
    # Omit None fields so we don't write e.g. {"subclass": null}
    data = pc.model_dump(by_alias=True, exclude_none=True)
    # Ensure JSON-friendly collections for prof fields
    for k in (
        "save_proficiencies",
        "skill_proficiencies",
        "armor_proficiencies",
        "weapon_proficiencies",
    ):
        if isinstance(data.get(k), set):
            data[k] = sorted(list(data[k]))
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")