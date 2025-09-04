from __future__ import annotations

import random
from typing import List, Tuple

from .death import reset_death_state
from .types import Combatant


def _con_mod(actor) -> int:
    return (getattr(actor, "con_score", 10) - 10) // 2


def roll_hit_die(faces: int, con_mod: int, rng: random.Random) -> Tuple[int, int]:
    """Returns (die_roll, total_with_con)."""
    d = rng.randint(1, faces)
    return d, d + con_mod


def short_rest(c: Combatant, *, spend: int, rng: random.Random | None = None) -> dict:
    """Spend up to 'spend' hit dice; heal and decrement hd_remaining."""
    rng = rng or random.Random()
    if spend <= 0 or c.hd_remaining <= 0:
        return {"healed": 0, "spent": 0, "rolls": []}
    to_spend = min(spend, c.hd_remaining)
    con = _con_mod(c.actor)

    rolls: List[int] = []
    healed = 0
    max_hp = c.max_hp or c.hp
    for _ in range(to_spend):
        d, total = roll_hit_die(c.hd_faces, con, rng)
        rolls.append(d)
        # apply each die step-by-step (can’t exceed max HP)
        delta = min(total, max_hp - c.hp)
        if delta <= 0:
            break
        c.hp += delta
        healed += delta
    c.hd_remaining -= (len(rolls) if healed > 0 else 0)
    return {"healed": healed, "spent": (len(rolls) if healed > 0 else 0), "rolls": rolls}


def long_rest(c: Combatant) -> dict:
    """Restore to max HP, regain up to half total hit dice (rounded down), clear common conditions, reset death saves."""
    before_hp = c.hp
    max_hp = c.max_hp or c.hp
    c.hp = max_hp

    regain = max(0, c.hd_total // 2)
    c.hd_remaining = min(c.hd_total, c.hd_remaining + regain)

    # Clear common short-duration conditions; you can extend this list later.
    for flag in ("poisoned", "restrained"):
        c.conditions.discard(flag)

    # Reset death saves (stays at 0 HP logic not relevant after long rest)
    if hasattr(c, "death"):
        reset_death_state(c.death)

    # Temp HP does NOT persist by RAW; drop it.
    c.temp_hp = 0

    return {"healed": c.hp - before_hp, "hd_regained": regain, "hp": c.hp, "hd_remaining": c.hd_remaining}

