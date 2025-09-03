from __future__ import annotations
from typing import Dict, List, Optional
from ..codex.armor import ArmorIndex, Armor


def dex_mod_for(character) -> int:
    if hasattr(character, "dex_score"):
        score = character.dex_score
    elif hasattr(character, "abilities"):
        score = getattr(character.abilities, "dex")
    else:
        score = getattr(character, "dex", 10)
    return (score - 10) // 2


def _dex_component(dex_mod: int, dex_cap: Optional[int], category: str) -> int:
    if dex_cap is None:
        return dex_mod
    if dex_cap == 0:
        return 0
    return dex_mod if dex_mod <= dex_cap else dex_cap


def compute_ac(character, armor_index: ArmorIndex) -> Dict[str, object]:
    pieces: List[str] = []
    notes: List[str] = []

    dex = dex_mod_for(character)

    base = 10
    dex_part = dex
    shield_bonus = 2 if getattr(character, "equipped_shield", False) else 0

    armor_name = getattr(character, "equipped_armor", None)
    if armor_name:
        armor: Armor = armor_index.get(armor_name)
        if armor.category == "shield":
            armor = None
            shield_bonus = 2
        else:
            base = armor.base_ac
            dex_part = _dex_component(dex, armor.dex_cap, armor.category)
            pieces.append(f"{armor.name} {base}")
            if armor.stealth_disadvantage:
                notes.append("stealth disadvantage")
            str_score = getattr(character, "str_score", None)
            if str_score is None and hasattr(character, "abilities"):
                str_score = getattr(character.abilities, "str")
            if str_score is None:
                str_score = getattr(character, "str", 10)
            if armor.str_min and str_score < armor.str_min:
                notes.append(f"Str {armor.str_min} req (speed −10 ft if unmet)")
    else:
        pieces.append("unarmored 10")

    pieces.append(f"Dex {dex_part:+d}")

    if shield_bonus:
        pieces.append("shield +2")

    ac = base + dex_part + shield_bonus
    return {"ac": ac, "components": pieces, "notes": notes}
