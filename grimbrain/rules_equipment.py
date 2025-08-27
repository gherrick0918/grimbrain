from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class KitItem:
    name: str
    qty: int = 1
    props: dict | None = None


def items(*pairs: tuple[str, int] | tuple[str, int, dict]) -> list[KitItem]:
    out: list[KitItem] = []
    for p in pairs:
        if len(p) == 2:
            n, q = p
            out.append(KitItem(n, q, None))
        else:
            n, q, pr = p
            out.append(KitItem(n, q, pr))
    return out


# A minimal SRD-ish baseline; expand later as needed
CLASS_KITS: Dict[str, list[KitItem]] = {
    "Wizard": items(
        ("Quarterstaff", 1),
        ("Arcane Focus (Wand)", 1),
        ("Component Pouch", 1),
        ("Scholar's Pack", 1),
        ("Spellbook", 1),
    ),
    "Fighter": items(
        ("Longsword", 1),
        ("Shield", 1, {"ac_bonus": 2}),
        ("Chain Mail", 1, {"ac": 16}),
        ("Explorer's Pack", 1),
    ),
    "Rogue": items(
        ("Rapier", 1),
        ("Shortbow", 1, {"ammo": "Arrows"}),
        ("Arrows", 20),
        ("Leather Armor", 1, {"ac": 11}),
        ("Burglar's Pack", 1),
        ("Thieves' Tools", 1),
    ),
    "Cleric": items(
        ("Mace", 1),
        ("Shield", 1, {"ac_bonus": 2}),
        ("Chain Mail", 1, {"ac": 16}),
        ("Holy Symbol", 1),
        ("Priest's Pack", 1),
    ),
    # …add more classes as you like
}

BACKGROUND_KITS: Dict[str, list[KitItem]] = {
    "Sage": items(
        ("Ink (1 oz bottle)", 1),
        ("Quill", 1),
        ("Parchment", 10),
        ("Small Knife", 1),
    ),
    "Soldier": items(
        ("Insignia of Rank", 1),
        ("Trophy from a Fallen Enemy", 1),
        ("Set of Dice", 1),
        ("Common Clothes", 1),
    ),
    "Acolyte": items(
        ("Holy Symbol", 1),
        ("Prayer Book", 1),
        ("Stick of Incense", 5),
        ("Common Clothes", 1),
    ),
}

BACKGROUND_LANGUAGES: Dict[str, list[str]] = {
    "Sage": ["Any"],  # choose later; we still record the slot
    "Acolyte": ["Celestial"],
}

BACKGROUND_TOOLS: Dict[str, list[str]] = {
    "Rogue": ["Thieves' Tools"],  # class-typical (you might keep this class-side if preferred)
    "Soldier": ["Gaming Set (Dice)"],
    "Guild Artisan": ["Tinker’s Tools"],
    "Sailor": ["Navigator’s Tools", "Vehicles (Water)"],
}
