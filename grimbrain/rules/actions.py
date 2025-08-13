from __future__ import annotations

from dataclasses import dataclass

from .core import AdvMode


@dataclass
class ActionState:
    """Transient per-creature combat flags."""

    dodge: bool = False
    hidden: bool = False
    help_advantage_token: bool = False


def apply_dodge(state: ActionState) -> None:
    state.dodge = True


def clear_dodge(state: ActionState) -> None:
    state.dodge = False


def apply_help(state: ActionState) -> None:
    state.help_advantage_token = True


def apply_hide(state: ActionState) -> None:
    state.hidden = True


def derive_attack_advantage(attacker: ActionState, defender: ActionState) -> AdvMode:
    adv = 0
    dis = 0
    if attacker.hidden:
        adv += 1
    if attacker.help_advantage_token:
        adv += 1
    if defender.dodge:
        dis += 1
    if adv and dis:
        return "normal"
    if adv:
        return "adv"
    if dis:
        return "dis"
    return "normal"


def consume_one_shot_flags(state: ActionState) -> None:
    state.help_advantage_token = False
    state.hidden = False
