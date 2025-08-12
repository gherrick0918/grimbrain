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


def roll_check(mod: int, dc: int, advantage: bool = False, seed: int | None = None) -> Dict[str, object]:
    """Perform an ability or skill check against ``dc``.

    Parameters
    ----------
    mod: int
        Ability or skill modifier to apply to the roll.
    dc: int
        Difficulty class to beat.
    advantage: bool, optional
        Roll with advantage if True.
    seed: int | None, optional
        Seed for deterministic results.

    Returns
    -------
    Dict[str, object]
        Mapping containing the raw roll (without modifier), the total, and
        whether the check succeeded.
    """

    result = roll(f"1d20+{mod}", seed=seed, adv=advantage)
    detail = result["detail"]
    roll_val = detail.get("chosen", detail.get("rolls", [0])[0])
    return {"roll": roll_val, "total": result["total"], "success": result["total"] >= dc}
