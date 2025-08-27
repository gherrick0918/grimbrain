from __future__ import annotations
from dataclasses import dataclass

# Saving throw proficiencies by class (SRD baseline)
CLASS_SAVE_PROFS = {
    "Barbarian": {"str", "con"},
    "Bard": {"dex", "cha"},
    "Cleric": {"wis", "cha"},
    "Druid": {"int", "wis"},
    "Fighter": {"str", "con"},
    "Monk": {"str", "dex"},
    "Paladin": {"wis", "cha"},
    "Ranger": {"str", "dex"},
    "Rogue": {"dex", "int"},
    "Sorcerer": {"con", "cha"},
    "Warlock": {"wis", "cha"},
    "Wizard": {"int", "wis"},
}

# Simple skill packages (backgrounds can add more later)
BACKGROUND_SKILLS = {
    "Sage": {"arcana", "history"},
    "Soldier": {"athletics", "intimidation"},
    "Acolyte": {"insight", "religion"},
}

# Full casters slots (L1–L9) – tuple per level (l1..l9)
FULL_CASTER_SLOTS = {
    1: (2, 0, 0, 0, 0, 0, 0, 0, 0),
    2: (3, 0, 0, 0, 0, 0, 0, 0, 0),
    3: (4, 2, 0, 0, 0, 0, 0, 0, 0),
    4: (4, 3, 0, 0, 0, 0, 0, 0, 0),
    5: (4, 3, 2, 0, 0, 0, 0, 0, 0),
    6: (4, 3, 3, 0, 0, 0, 0, 0, 0),
    7: (4, 3, 3, 1, 0, 0, 0, 0, 0),
    8: (4, 3, 3, 2, 0, 0, 0, 0, 0),
    9: (4, 3, 3, 3, 1, 0, 0, 0, 0),
    10: (4, 3, 3, 3, 2, 0, 0, 0, 0),
    11: (4, 3, 3, 3, 2, 1, 0, 0, 0),
    12: (4, 3, 3, 3, 2, 1, 0, 0, 0),
    13: (4, 3, 3, 3, 2, 1, 1, 0, 0),
    14: (4, 3, 3, 3, 2, 1, 1, 0, 0),
    15: (4, 3, 3, 3, 2, 1, 1, 1, 0),
    16: (4, 3, 3, 3, 2, 1, 1, 1, 0),
    17: (4, 3, 3, 3, 2, 1, 1, 1, 1),
    18: (4, 3, 3, 3, 3, 1, 1, 1, 1),
    19: (4, 3, 3, 3, 3, 2, 1, 1, 1),
    20: (4, 3, 3, 3, 3, 2, 2, 1, 1),
}

# Half-caster / third-caster progression can be added later when needed.

# Pact magic (Warlock) – slots per level (level, #slots, slot level)
PACT_MAGIC = {
    1: (1, 1),
    2: (2, 1),
    3: (2, 2),
    4: (2, 2),
    5: (2, 3),
    6: (2, 3),
    7: (2, 4),
    8: (2, 4),
    9: (2, 5),
    10: (2, 5),
    11: (3, 5),
    12: (3, 5),
    13: (3, 5),
    14: (3, 5),
    15: (3, 5),
    16: (3, 5),
    17: (4, 5),
    18: (4, 5),
    19: (4, 5),
    20: (4, 5),
}
