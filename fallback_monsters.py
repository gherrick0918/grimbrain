# Minimal hardcoded stat blocks for common low-CR goblins used when the vector store
# or external monster data is unavailable. These mirror the entries originally
# embedded in query_router.py but are split out so that lightweight scripts such
# as the --play CLI can import them without pulling in the heavy LLM dependencies.

FALLBACK_MONSTERS: dict[str, dict] = {
    "goblin": {
        "name": "Goblin",
        "source": "MM",
        "ac": "15 (leather armor, shield)",
        "hp": "7 (2d6)",
        "speed": "30 ft.",
        "str": 8,
        "dex": 14,
        "con": 10,
        "int": 10,
        "wis": 8,
        "cha": 8,
        "traits": [
            {
                "name": "Nimble Escape",
                "text": "The goblin can take the Disengage or Hide action as a bonus action on each of its turns.",
            }
        ],
        "actions": [
            {
                "name": "Scimitar",
                "text": "Melee Weapon Attack: +4 to hit, reach 5 ft., one target. Hit: 5 (1d6 + 2) slashing damage.",
            },
            {
                "name": "Shortbow",
                "text": "Ranged Weapon Attack: +4 to hit, range 80/320 ft., one target. Hit: 5 (1d6 + 2) piercing damage.",
            },
        ],
        "actions_struct": [
            {
                "name": "Scimitar",
                "attack_bonus": 4,
                "type": "melee",
                "reach_or_range": "reach 5 ft.",
                "target": "one target",
                "hit_text": "5 (1d6 + 2) slashing damage.",
                "damage_dice": "1d6 + 2",
                "damage_type": "slashing",
            },
            {
                "name": "Shortbow",
                "attack_bonus": 4,
                "type": "ranged",
                "reach_or_range": "range 80/320 ft.",
                "target": "one target",
                "hit_text": "5 (1d6 + 2) piercing damage.",
                "damage_dice": "1d6 + 2",
                "damage_type": "piercing",
            },
        ],
        "reactions": [],
        "provenance": ["MM · Goblin"],
    },
    "goblin boss": {
        "name": "Goblin Boss",
        "source": "MM",
        "ac": "17 (chain shirt, shield)",
        "hp": "21 (6d6)",
        "speed": "30 ft.",
        "str": 10,
        "dex": 14,
        "con": 10,
        "int": 10,
        "wis": 8,
        "cha": 10,
        "traits": [
            {
                "name": "Nimble Escape",
                "text": "The goblin can take the Disengage or Hide action as a bonus action on each of its turns.",
            }
        ],
        "actions": [
            {
                "name": "Multiattack",
                "text": "The goblin makes two attacks with its scimitar. It can replace one attack with a javelin attack.",
            },
            {
                "name": "Scimitar",
                "text": "Melee Weapon Attack: +4 to hit, reach 5 ft., one target. Hit: 5 (1d6 + 2) slashing damage.",
            },
            {
                "name": "Javelin",
                "text": "Ranged Weapon Attack: +4 to hit, range 30/120 ft., one target. Hit: 5 (1d6 + 2) piercing damage.",
            },
        ],
        "actions_struct": [
            {
                "name": "Scimitar",
                "attack_bonus": 4,
                "type": "melee",
                "reach_or_range": "reach 5 ft.",
                "target": "one target",
                "hit_text": "5 (1d6 + 2) slashing damage.",
                "damage_dice": "1d6 + 2",
                "damage_type": "slashing",
            },
            {
                "name": "Javelin",
                "attack_bonus": 4,
                "type": "ranged",
                "reach_or_range": "range 30/120 ft.",
                "target": "one target",
                "hit_text": "5 (1d6 + 2) piercing damage.",
                "damage_dice": "1d6 + 2",
                "damage_type": "piercing",
            },
        ],
        "reactions": [
            {
                "name": "Redirect Attack",
                "text": "When a creature the goblin can see targets it with an attack, the goblin chooses another goblin within 5 ft. of it; the two goblins swap places, and the chosen goblin becomes the target instead.",
            }
        ],
        "provenance": ["MM · Goblin Boss"],
    },
    "booyahg whip": {
        "name": "Booyahg Whip",
        "source": "VGM",
        "ac": "15",
        "hp": "7 (2d6)",
        "speed": "30 ft.",
        "str": 8,
        "dex": 14,
        "con": 10,
        "int": 10,
        "wis": 8,
        "cha": 8,
        "traits": [],
        "actions": [],
        "actions_struct": [],
        "reactions": [],
        "provenance": ["VGM · Booyahg Whip"],
    },
}
