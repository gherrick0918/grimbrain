from __future__ import annotations
from typing import Tuple, List
from .types import Combatant
import math


def apply_defenses(
    raw_total: int,
    damage_type: str,
    defender: Combatant
) -> Tuple[int, List[str], int]:
    """
    Returns (final_total_hp_loss, notes, temp_hp_spent).
    Order: apply immunity/resistance/vulnerability -> then temp HP soak.
    Rounding: resistance halves (round down), vulnerability doubles.
    """
    notes: List[str] = []
    if damage_type in defender.immune:
        notes.append(f"immune to {damage_type} (0)")
        return 0, notes, 0

    factor = 1.0
    if damage_type in defender.resist:
        factor *= 0.5
        notes.append(f"resistant to {damage_type} (halved)")
    if damage_type in defender.vulnerable:
        factor *= 2.0
        notes.append(f"vulnerable to {damage_type} (doubled)")

    adjusted = math.floor(raw_total * factor)

    thp_spent = 0
    if defender.temp_hp > 0 and adjusted > 0:
        thp_spent = min(defender.temp_hp, adjusted)
        defender.temp_hp -= thp_spent
        adjusted -= thp_spent
        notes.append(f"temp HP soaked {thp_spent}")

    return max(0, adjusted), notes, thp_spent
