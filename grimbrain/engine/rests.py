from __future__ import annotations

import random
from typing import Iterable, Mapping

from .dice import roll
from ..models import PC


def _check_restable(pc: PC) -> None:
    if pc.hp <= 0:
        raise ValueError(f"{pc.name} is dead and cannot rest")
    if getattr(pc, "in_combat", False):
        raise ValueError(f"{pc.name} cannot rest during combat")


def apply_short_rest(
    pcs: Iterable[PC],
    rng: random.Random | None = None,
    spends: Mapping[str, int] | None = None,
) -> dict:
    """Apply a short rest to PCs, returning heal/roll details.

    Parameters
    ----------
    pcs:
        Iterable of PCs to rest.
    rng:
        Optional RNG for deterministic results.
    spends:
        Optional mapping of PC name to number of Hit Dice to spend.
        Defaults to 1 per PC if not provided.
    """

    rng = rng or random.Random()
    deltas: dict[str, dict] = {}
    for pc in pcs:
        _check_restable(pc)
        spend_req = spends.get(pc.name, 1) if spends else 1
        spend = min(spend_req, max(pc.hit_dice_remaining, 0))
        rolls: list[int] = []
        total = 0
        for _ in range(spend):
            seed = rng.randint(0, 10_000_000)
            die_size = int(pc.hit_die.lstrip("d"))
            die = roll(f"1d{die_size}", seed=seed)["total"]
            rolls.append(die)
            total += max(0, die + pc.con_mod)
        before = pc.hp
        pc.hp = min(pc.hp + total, pc.max_hp)
        pc.hit_dice_remaining = max(pc.hit_dice_remaining - spend, 0)
        deltas[pc.name] = {
            "healed": pc.hp - before,
            "rolls": rolls,
            "spent": spend,
        }
    return deltas


def apply_long_rest(pcs: Iterable[PC]) -> dict:
    """Fully heal PCs and recover Hit Dice."""
    deltas: dict[str, dict] = {}
    for pc in pcs:
        _check_restable(pc)
        before = pc.hp
        pc.hp = pc.max_hp
        recover = pc.hit_dice_total // 2
        missing = pc.hit_dice_total - pc.hit_dice_remaining
        recover = min(recover, missing)
        pc.hit_dice_remaining += recover
        # restore spell slots to max
        pc.spell_slots = pc.spell_slots_total.copy()
        deltas[pc.name] = {
            "healed": pc.hp - before,
            "hd_regained": recover,
        }
    return deltas
