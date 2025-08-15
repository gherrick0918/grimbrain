"""Utility helpers for the command-line interface."""

from __future__ import annotations

from dataclasses import asdict, replace
from typing import Any

from grimbrain.engine.session import Session
from grimbrain.engine.combat import Combatant
from grimbrain.rules import ActionState, ConditionFlags


def _apply_damage(target: Combatant, amount: int, attack_type: str = "melee", crit: bool = False) -> None:
    if getattr(target, "defeated", False):
        return
    target.hp -= amount
    if target.hp > 0:
        return
    target.hp = 0
    if getattr(target, "downed", False) or getattr(target, "stable", False):
        was_stable = getattr(target, "stable", False)
        target.stable = False
        fails = 2 if crit and attack_type == "melee" else 1
        target.death_failures += fails
        if was_stable:
            print(f"{target.name} suffers {fails} failure{'s' if fails > 1 else ''}")
        else:
            print(f"{target.name} suffers {fails} death save failure{'s' if fails > 1 else ''}")
        print(f"[Downed S:{getattr(target, 'death_successes', 0)}/F:{target.death_failures}]")
        if target.death_failures >= 3:
            target.defeated = True
            print(f"{target.name} dies")
    else:
        target.downed = True
        target.death_successes = 0
        target.death_failures = 0
        print(f"{target.name} is downed")


def heal_target(target: Combatant, amount: int) -> str:
    if getattr(target, "defeated", False):
        return f"{target.name} is dead."
    before = target.hp
    target.hp = min(target.hp + amount, getattr(target, "max_hp", target.hp + amount))
    cleared = False
    if before <= 0:
        target.downed = False
        target.stable = False
        target.death_successes = 0
        target.death_failures = 0
        target.defeated = False
        cleared = True
    note = "; death saves cleared" if cleared else ""
    return f"{target.name} heals {amount} (HP {before} -> {target.hp}){note}"


def _print_status(
    round_num: int,
    combatants: list[Combatant],
    action_state: dict[str, ActionState] | None = None,
    condition_state: dict[str, ConditionFlags] | None = None,
) -> None:
    print(f"Round {round_num}")
    order = ", ".join(c.name for c in combatants)
    print(f"Initiative: {order}")
    for c in combatants:
        hp = f"{c.hp} HP"
        tags = ""
        if action_state is not None:
            st = action_state.get(c.name)
            if st:
                if st.dodge:
                    tags += " [Dodge]"
                if st.hidden:
                    tags += " [Hidden]"
                if st.help_advantage_token:
                    tags += " [Help]"
        if condition_state is not None:
            cf = condition_state.get(c.name)
            if cf:
                if cf.prone:
                    tags += " [Prone]"
                if cf.restrained:
                    tags += " [Restrained]"
                if cf.frightened:
                    tags += " [Frightened]"
                if cf.grappled:
                    tags += " [Grappled]"
        if c.defeated:
            tags += " [Dead]"
        elif c.hp <= 0:
            if getattr(c, "stable", False):
                tags += " [Stable]"
            else:
                tags += f" [Downed S:{getattr(c, 'death_successes', 0)}/F:{getattr(c, 'death_failures', 0)}]"
        line = f"{c.name}: {hp}, AC {c.ac}{tags}"
        if getattr(c, "hit_die", None):
            line += f"; HD {c.hit_die} {getattr(c, 'hit_dice_remaining', 0)}/{getattr(c, 'hit_dice_total', 0)}"
        slots_tot = getattr(c, "spell_slots_total", {})
        if slots_tot:
            parts = [f"L{lvl} {c.spell_slots.get(lvl,0)}/{tot}" for lvl, tot in sorted(slots_tot.items())]
            line += f"; Slots: {' '.join(parts)}"
        print(line)


def _check_victory(combatants: list[Combatant]) -> str | None:
    party_alive = any(c.side == "party" and c.hp > 0 for c in combatants)
    monsters_alive = any(c.side == "monsters" and c.hp > 0 for c in combatants)
    if not party_alive:
        return "monsters"
    if not monsters_alive:
        return "party"
    return None


def _save_game(
    path: str,
    seed: int | None,
    round_num: int,
    turn: int,
    combatants: list[Combatant],
    conditions: dict[str, ConditionFlags] | None = None,
) -> None:
    step = {
        "round": round_num,
        "turn": turn,
        "combatants": [_serialize_combatant(c) for c in combatants],
    }
    if conditions:
        step["conditions"] = {n: asdict(f) for n, f in conditions.items()}
    sess = Session(scene="play", seed=seed, steps=[step])
    sess.save(path)
    print(f"Saved to {path}")


def _load_game(path: str):
    sess = Session.load(path)
    if sess.steps:
        data = sess.steps[0]
        round_num = data.get("round", 1)
        turn = data.get("turn", 0)
        combatants = _deserialize_combatants(data.get("combatants", []))
        cond_data = data.get("conditions", {})
        conditions = {n: ConditionFlags(**v) for n, v in cond_data.items()}
    else:
        round_num = 1
        turn = 0
        combatants = []
        conditions = {}
    return sess.seed, round_num, turn, combatants, conditions


def _edit_distance_one(a: str, b: str) -> bool:
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1
    if len(a) + 1 == len(b):
        for i in range(len(b)):
            if a[:i] == b[:i] and a[i:] == b[i + 1 :]:
                return True
        return False
    if len(b) + 1 == len(a):
        for i in range(len(a)):
            if a[:i] == b[:i] and a[i + 1 :] == b[i:]:
                return True
        return False
    return False


def _normalize_cmd(cmd: str) -> str:
    aliases = {"a": "attack", "atk": "attack", "c": "cast", "s": "status", "q": "quit"}
    if cmd in aliases:
        return aliases[cmd]
    known = [
        "attack",
        "cast",
        "status",
        "quit",
        "end",
        "save",
        "load",
        "actions",
        "grapple",
        "shove",
        "stand",
    ]
    for k in known:
        if _edit_distance_one(cmd, k):
            return k
    return cmd


# Functions that depend on helpers defined above
# These are thin wrappers to avoid circular imports when referenced from main.py

def _serialize_combatant(c: Combatant) -> dict:
    return {
        "name": c.name,
        "ac": c.ac,
        "hp": c.hp,
        "side": c.side,
        "dex_mod": getattr(c, "dex_mod", 0),
        "str_mod": getattr(c, "str_mod", 0),
        "attacks": c.attacks,
        "defeated": c.defeated,
        "init": getattr(c, "init", 0),
        "downed": getattr(c, "downed", False),
        "stable": getattr(c, "stable", False),
        "ds_success": getattr(c, "death_successes", 0),
        "ds_fail": getattr(c, "death_failures", 0),
        "max_hp": getattr(c, "max_hp", c.hp),
    }


def _deserialize_combatants(data: list[dict]) -> list[Combatant]:
    combs: list[Combatant] = []
    for cd in data:
        c = Combatant(
            cd["name"],
            cd["ac"],
            cd["hp"],
            cd["attacks"],
            cd["side"],
            cd.get("dex_mod", 0),
            max_hp=cd.get("max_hp", cd["hp"]),
        )
        c.defeated = cd.get("defeated", False)
        c.init = cd.get("init", 0)
        c.str_mod = cd.get("str_mod", 0)
        c.downed = cd.get("downed", False)
        c.stable = cd.get("stable", False)
        c.death_successes = cd.get("ds_success", 0)
        c.death_failures = cd.get("ds_fail", 0)
        combs.append(c)
    combs.sort(key=lambda c: c.init, reverse=True)
    return combs
