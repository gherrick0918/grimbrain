
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Conditions:
    prone: bool = False
    restrained: bool = False
    frightened: bool = False
    grappled: bool = False

# Alias for compatibility with code expecting ConditionFlags
ConditionFlags = Conditions

from dataclasses import dataclass

from .core import AdvMode


@dataclass(frozen=True)
class Conditions:
    prone: bool = False
    restrained: bool = False
    frightened: bool = False
    grappled: bool = False


def derive_condition_advantage(attacker: Conditions, defender: Conditions, melee: bool) -> AdvMode:
    """Return net advantage/disadvantage from attacker/defender conditions."""
    adv = False
    dis = False

    # Defender effects
    if defender.restrained:
        adv = True
    if defender.prone:
        if melee:
            adv = True
        else:
            dis = True

    # Attacker effects
    if attacker.restrained:
        dis = True
    if attacker.prone:
        dis = True
    if attacker.frightened:
        dis = True

    if adv and dis:
        return "normal"
    if adv:
        return "adv"
    if dis:
        return "dis"
    return "normal"
