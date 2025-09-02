from __future__ import annotations
from typing import List
from ..codex.weapons import Weapon

def weapon_notes(weapon: Weapon) -> List[str]:
    notes: List[str] = []

    # Loading (generic)
    if weapon.has_prop("loading"):
        notes.append("Loading: only one shot per action/bonus/reaction.")

    # Weapon-specific "special" notes
    if weapon.has_prop("special"):
        n = weapon.name.lower()
        if n == "lance":
            notes.append("Lance: disadvantage if target is within 5 ft; two-handed when not mounted.")
        if n == "net":
            notes.append(
                "Net: on hit, Large or smaller is restrained until freed; action to escape (STR DC 10) "
                "or deal 5 slashing to the net (AC 10) to free (net destroyed). No effect on Huge+ or formless."
            )

    return notes
