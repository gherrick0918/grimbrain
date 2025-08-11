"""Common combat checks built on the deterministic dice roller."""
from __future__ import annotations

from typing import Dict

from .dice import roll


def attack_roll(to_hit: int, ac: int, seed: int | None) -> Dict[str, object]:
    """Resolve an attack roll against ``ac``.

    Returns a mapping with ``hit`` (bool) and the underlying dice roll data.
    """
    result = roll(f"1d20+{to_hit}", seed=seed)
    return {"hit": result["total"] >= ac, "detail": result}


def damage_roll(dice_expr: str, seed: int | None) -> Dict[str, object]:
    """Roll damage using ``dice_expr``."""
    return roll(dice_expr, seed=seed)


def saving_throw(dc: int, mod: int, seed: int | None, adv: bool = False, disadv: bool = False) -> Dict[str, object]:
    """Perform a saving throw against ``dc``.

    Advantage and disadvantage flags are passed through to the dice roller.
    Returns mapping with ``success`` and roll ``detail``.
    """
    result = roll(f"1d20+{mod}", seed=seed, adv=adv, disadv=disadv)
    return {"success": result["total"] >= dc, "detail": result}
