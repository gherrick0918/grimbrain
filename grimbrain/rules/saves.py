from __future__ import annotations

from .core import AdvMode, _d20


def save_dc(prof_bonus: int, ability_mod: int, misc: int = 0, base: int = 8) -> int:
    """Assemble a saving throw DC from its parts."""
    return base + prof_bonus + ability_mod + misc


def roll_save(dc: int, bonus: int, adv: AdvMode = "normal", rng=None):
    """
    Roll a d20 saving throw with optional advantage/disadvantage.
    Returns (success, total, face).
    Natural 20/1 do not auto succeed/fail; only the total vs DC matters.
    """
    import random
    rng = rng or random.Random()
    a = _d20(rng)
    if adv == "normal":
        face = a
    else:
        b = _d20(rng)
        face = max(a, b) if adv == "adv" else min(a, b)
    total = face + bonus
    return total >= dc, total, face
