from __future__ import annotations
from typing import Dict, List

# Minimal SRD-ish seed lists; expand freely later.
SPELLS_BY_CLASS: Dict[str, Dict[int, List[str]]] = {
    "Wizard": {
        0: ["Prestidigitation", "Mage Hand"],
        1: ["Magic Missile", "Shield", "Detect Magic"],
        2: ["Misty Step", "Mirror Image"],
    },
    "Cleric": {
        0: ["Guidance", "Sacred Flame"],
        1: ["Cure Wounds", "Bless"],
    },
    "Warlock": {
        0: ["Eldritch Blast"],
        1: ["Hex", "Armor of Agathys"],
        2: ["Invisibility"],
    },
    # add more as needed (Druid, Bard, Sorcerer, etc.)
}

CASTING_ABILITY: Dict[str, str] = {
    "Wizard": "int",
    "Cleric": "wis",
    "Druid": "wis",
    "Bard": "cha",
    "Sorcerer": "cha",
    "Warlock": "cha",
    "Paladin": "cha",
    "Ranger": "wis",
    # EK/AT still use int for their spells typically; handled via subclass if desired
}

# Prepared-caster classes vs known-caster classes (baseline SRD assumption)
PREPARED_CASTER = {"Cleric", "Druid", "Paladin", "Wizard"}  # Wizards technically prepare from a spellbook
KNOWN_CASTER = {"Bard", "Sorcerer", "Warlock", "Ranger"}     # (Ranger prepares in 5e; feel free to move it)
