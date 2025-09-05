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
    total = d + ability_mod(actor, ability)
    return (total >= dc, d, (d1, d2))

