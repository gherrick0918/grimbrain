from __future__ import annotations
from typing import Literal, Tuple
import re

Die = Tuple[int, int]  # (count, faces)
_MODE = Literal["none", "advantage", "disadvantage"]

def combine_modes(a: _MODE, b: _MODE) -> _MODE:
    """Combine two advantage states.

    Any combination of advantage and disadvantage cancels to "none". If one side
    is "none", the other side wins. Otherwise the inputs match and are returned
    unchanged.
    """
    if a == b:
        return a
    if a == "none":
        return b
    if b == "none":
        return a
    return "none"

_DIE_PAT = re.compile(r"^(\d+)d(\d+)$")

def parse_die(die: str) -> Die | None:
    m = _DIE_PAT.match(die)
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)))

def double_die_text(die: str) -> str:
    parsed = parse_die(die)
    if not parsed:
        return die  # numbers like "1" or "—" stay as-is for crit
    n, f = parsed
    return f"{n*2}d{f}"

def roll_outcome(d: int, attack_bonus: int, ac: int) -> Tuple[bool, bool]:
    """
    Single d20 outcome -> (is_hit, is_crit) using 5e rules:
      - nat 1 always misses
      - nat 20 always hits & crits
      - otherwise hit if d + attack_bonus >= ac
    """
    if d == 1:
        return (False, False)
    if d == 20:
        return (True, True)
    return (d + attack_bonus >= ac, False)

def _pair_iter(mode: _MODE):
    if mode == "none":
        for d in range(1, 21):
            yield (d,)
    else:
        for d1 in range(1, 21):
            for d2 in range(1, 21):
                yield (d1, d2)

def _reduce_to_result(ds: tuple[int, ...], mode: _MODE) -> int:
    if mode == "none":
        return ds[0]
    return max(ds) if mode == "advantage" else min(ds)

def hit_probabilities(attack_bonus: int, ac: int, mode: _MODE = "none"):
    """
    Exact probabilities under d20 core rules with nat1/nat20 handling.
    Returns dict with floats in [0,1]: {'hit': p_any_hit, 'crit': p_crit, 'normal': p_noncrit_hit}
    """
    total = 20 if mode == "none" else 400
    hits = crits = 0
    for ds in _pair_iter(mode):
        d = _reduce_to_result(ds, mode)
        is_hit, is_crit = roll_outcome(d, attack_bonus, ac)
        hits += 1 if is_hit else 0
        crits += 1 if is_crit else 0
    p_hit = hits / total
    p_crit = crits / total
    return {"hit": p_hit, "crit": p_crit, "normal": p_hit - p_crit}
