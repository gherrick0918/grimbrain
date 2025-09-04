from __future__ import annotations
from typing import Tuple
import random

from .types import Combatant


def _roll_2d4_plus_2(rng: random.Random) -> Tuple[list[int], int]:
    r1 = rng.randint(1, 4)
    r2 = rng.randint(1, 4)
    return [r1, r2], r1 + r2 + 2


def drink_potion_of_healing(c: Combatant, *, rng: random.Random) -> dict:
    """Action: drink 1 potion if available. Returns log dict."""
    count = c.consumables.get("Potion of Healing", 0)
    if count <= 0:
        return {"ok": False, "reason": "no Potion of Healing"}
    # cannot drink while dead; if at 0 HP & unconscious you'd need an ally — keep it simple: block here
    if c.hp <= 0:
        return {"ok": False, "reason": "unconscious"}
    rolls, total = _roll_2d4_plus_2(rng)
    max_hp = c.max_hp or c.hp
    delta = max(0, min(total, max_hp - c.hp))
    c.hp += delta
    c.consumables["Potion of Healing"] = count - 1
    return {"ok": True, "healed": delta, "rolls": rolls, "total": total, "remaining": c.consumables["Potion of Healing"]}
