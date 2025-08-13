
from __future__ import annotations
# --- Adv combiner (5e: adv + dis cancel) --------------------------------------
from typing import Literal

def combine_adv(*modes: Literal["normal", "adv", "dis"]) -> Literal["normal", "adv", "dis"]:
    """Any adv + any dis -> normal; else adv if any adv; else dis if any dis; else normal."""
    has_adv = any(m == "adv" for m in modes)
    has_dis = any(m == "dis" for m in modes)
    if has_adv and has_dis:
        return "normal"
    if has_adv:
        return "adv"
    if has_dis:
        return "dis"
    return "normal"

from dataclasses import dataclass

from .core import AdvMode  # If still needed elsewhere, otherwise remove


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


def derive_attack_advantage(attacker: ActionState, defender: ActionState) -> Literal["normal", "adv", "dis"]:
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
