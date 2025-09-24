from __future__ import annotations

from typing import Literal, Tuple
import random

from ..rules.attack_math import combine_modes
from .types import Combatant

Ability = Literal["STR", "DEX", "CON", "INT", "WIS", "CHA"]


def ability_mod(actor, key: Ability) -> int:
    score = {
        "STR": getattr(actor, "str_score", 10),
        "DEX": getattr(actor, "dex_score", 10),
        "CON": getattr(actor, "con_score", 10),
        "INT": getattr(actor, "int_score", 10),
        "WIS": getattr(actor, "wis_score", 10),
        "CHA": getattr(actor, "cha_score", 10),
    }.get(key, 10)
    return (score - 10) // 2


def roll_save(
    actor,
    ability: Ability,
    dc: int,
    *,
    mode: Literal["none", "advantage", "disadvantage"] = "none",
    rng: random.Random | None = None,
    combatant: Combatant | None = None,
) -> Tuple[bool, int, tuple[int, int]]:
    rng = rng or random.Random()
    d1, d2 = rng.randint(1, 20), rng.randint(1, 20)
    # PR40: Dodge grants advantage on DEX saves
    if ability == "DEX" and combatant is not None and combatant.dodging:
        mode = combine_modes(mode, "advantage")

    if mode == "advantage":
        d = max(d1, d2)
    elif mode == "disadvantage":
        d = min(d1, d2)
    else:
        d = d1

    prof_bonus = 0
    pb = None
    if combatant is not None and hasattr(combatant, "proficiency_bonus"):
        pb = getattr(combatant, "proficiency_bonus")
    if pb is None and hasattr(actor, "proficiency_bonus"):
        pb = getattr(actor, "proficiency_bonus")
    if pb is None and hasattr(actor, "pb"):
        pb = getattr(actor, "pb")
    pb = int(pb) if pb is not None else 0

    save_set = set()
    if combatant is not None and getattr(combatant, "prof_saves", None):
        save_set = {str(s).upper() for s in combatant.prof_saves}
    elif hasattr(actor, "prof_saves"):
        raw = getattr(actor, "prof_saves")
        if raw:
            save_set = {str(s).upper() for s in raw}
    if ability.upper() in save_set:
        prof_bonus = pb

    total = d + ability_mod(actor, ability) + prof_bonus
    return (total >= dc, d, (d1, d2))

