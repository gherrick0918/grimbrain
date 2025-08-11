"""Deterministic dice roller supporting advantage/disadvantage."""
from __future__ import annotations

import random
import re
from typing import Dict, List, Optional

DICE_RE = re.compile(r"^(?P<num>\d*)d(?P<sides>\d+)(?P<mod>[+-]\d+)?$", re.IGNORECASE)


def roll(expr: str, seed: int | None = None, adv: bool = False, disadv: bool = False) -> Dict[str, object]:
    """Roll dice described by ``expr``.

    Parameters
    ----------
    expr: str
        Dice expression of the form ``XdY+Z``. ``X`` defaults to 1 and ``Z`` to 0.
    seed: int | None
        Optional seed for deterministic results.
    adv, disadv: bool
        If ``adv`` is True, roll with advantage. If ``disadv`` is True, roll with
        disadvantage. These options only apply to ``1d20`` rolls.

    Returns
    -------
    dict
        ``{"total": int, "detail": dict}``
    """
    if adv and disadv:
        raise ValueError("Cannot roll with both advantage and disadvantage")

    m = DICE_RE.fullmatch(expr.replace(" ", ""))
    if not m:
        raise ValueError(f"Invalid dice expression: {expr}")

    num = int(m.group("num") or 1)
    sides = int(m.group("sides"))
    mod = int(m.group("mod") or 0)

    rng = random.Random(seed)

    detail: Dict[str, object]
    if adv or disadv:
        if not (num == 1 and sides == 20):
            raise ValueError("Advantage/disadvantage only supported for 1d20 rolls")
        first = rng.randint(1, sides)
        second = rng.randint(1, sides)
        chosen = max(first, second) if adv else min(first, second)
        total = chosen + mod
        detail = {
            "rolls": [first, second],
            "modifier": mod,
            "chosen": chosen,
            "advantage": adv,
            "disadvantage": disadv,
        }
    else:
        rolls: List[int] = [rng.randint(1, sides) for _ in range(num)]
        total = sum(rolls) + mod
        detail = {"rolls": rolls, "modifier": mod}

    return {"total": total, "detail": detail}
