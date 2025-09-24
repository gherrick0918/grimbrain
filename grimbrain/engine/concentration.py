from __future__ import annotations
from typing import Optional
import random

from .types import Combatant
from .saves import roll_save

def start_concentration(c: Combatant, label: str) -> None:
    # Starting new concentration ends previous (RAW)
    c.concentration = label

def drop_concentration(c: Combatant, reason: str = "") -> str:
    if not c.concentration:
        return ""
    lab = c.concentration
    c.concentration = None
    return f"concentration on {lab} ends{(' — ' + reason) if reason else ''}"

def check_concentration_on_damage(c: Combatant, damage_taken: int, *, rng: random.Random,
                                  has_war_caster: bool = False) -> tuple[bool, int]:
    if not c.concentration or damage_taken <= 0:
        return True, 0
    dc = max(10, damage_taken // 2)
    mode = "advantage" if has_war_caster else "none"
    ok, d, _ = roll_save(c.actor, "CON", dc, mode=mode, rng=rng, combatant=c)
    if not ok:
        drop_concentration(c, f"failed CON save DC {dc} (rolled {d}+mod)")
    return ok, dc
