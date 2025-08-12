from __future__ import annotations

import random
from typing import Iterable

from .dice import roll
from ..models import PC


def apply_short_rest(pcs: Iterable[PC], rng: random.Random | None = None) -> dict:
    """Apply a short rest to PCs, returning healing deltas."""
    rng = rng or random.Random()
    deltas: dict[str, int] = {}
    for pc in pcs:
        seed = rng.randint(0, 10_000_000)
        heal = roll("1d8", seed=seed)["total"] + getattr(pc, "con_mod", 0)
        heal = max(1, heal)
        before = pc.hp
        pc.hp = min(pc.hp + heal, pc.max_hp)
        deltas[pc.name] = pc.hp - before
    return deltas


def apply_long_rest(pcs: Iterable[PC]) -> dict:
    """Fully heal PCs."""
    deltas: dict[str, int] = {}
    for pc in pcs:
        before = pc.hp
        pc.hp = pc.max_hp
        deltas[pc.name] = pc.hp - before
    return deltas
