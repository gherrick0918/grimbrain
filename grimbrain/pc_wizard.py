from __future__ import annotations

import json
from pathlib import Path
from typing import List

from .models import PC, dump_model

PRESETS = {
    "fighter": [
        {
            "name": "Malrick",
            "ac": 16,
            "hp": 20,
            "attacks": [
                {"name": "Longsword", "to_hit": 5, "damage_dice": "1d8+3", "type": "melee"}
            ],
        },
        {
            "name": "Brynn",
            "ac": 14,
            "hp": 16,
            "attacks": [
                {"name": "Shortsword", "to_hit": 4, "damage_dice": "1d6+2", "type": "melee"}
            ],
        },
    ],
    "rogue": [
        {
            "name": "Brynn",
            "ac": 14,
            "hp": 16,
            "attacks": [
                {"name": "Dagger", "to_hit": 5, "damage_dice": "1d4+3", "type": "melee"}
            ],
        }
    ],
    "wizard": [
        {
            "name": "Elora",
            "ac": 12,
            "hp": 12,
            "attacks": [
                {"name": "Fire Bolt", "to_hit": 5, "damage_dice": "1d10", "type": "ranged"}
            ],
        }
    ],
}


def _interactive_party() -> List[dict] | None:
    print("PC Wizard: create up to 2 PCs. Leave name blank to finish.")
    party: List[dict] = []
    for _ in range(2):
        name = input("Name: ").strip()
        if not name:
            break
        ac = int(input("AC: ").strip())
        hp = int(input("HP: ").strip())
        atk_name = input("Attack name: ").strip()
        to_hit = int(input("To-hit bonus: ").strip())
        dmg = input("Damage dice (e.g., 1d6+3): ").strip()
        atk_type = input("Attack type (melee|ranged): ").strip() or "melee"
        party.append(
            {
                "name": name,
                "ac": ac,
                "hp": hp,
                "attacks": [
                    {
                        "name": atk_name,
                        "to_hit": to_hit,
                        "damage_dice": dmg,
                        "type": atk_type,
                    }
                ],
            }
        )
    return party or None


def main(out: str | None = None, preset: str | None = None) -> Path | None:
    if preset:
        party = PRESETS.get(preset)
    else:
        party = _interactive_party()
    if not party:
        print("No characters created.")
        return None

    pcs = [PC(**pc) for pc in party]
    data = {"party": [dump_model(pc) for pc in pcs]}
    path = Path(out or "pc.json")
    path.write_text(json.dumps(data, indent=2))
    print(f"Wrote party to {path} ({len(pcs)} characters).")
    return path
