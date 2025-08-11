"""Minimal combat round resolution."""
from __future__ import annotations

import random
from typing import Dict, List

from .checks import attack_roll, damage_roll
from .dice import roll
from models import MonsterSidecar, PC


class Combatant:
    """Internal mutable combatant state."""

    def __init__(self, name: str, ac: int, hp: int, attacks: List[Dict[str, object]], side: str, dex_mod: int = 0):
        self.name = name
        self.ac = ac
        self.hp = hp
        self.attacks = attacks
        self.side = side
        self.dex_mod = dex_mod
        self.defeated = False

    def to_state(self) -> Dict[str, object]:
        return {"name": self.name, "hp": self.hp, "defeated": self.defeated}


def _parse_monster(mon: MonsterSidecar) -> Combatant:
    ac = int(mon.ac.split()[0])
    hp = int(mon.hp.split()[0])
    dex_mod = (mon.dex - 10) // 2
    attacks: List[Dict[str, object]] = []
    for a in mon.actions_struct:
        attacks.append({"to_hit": a.attack_bonus, "damage_dice": a.damage_dice, "type": a.type})
    return Combatant(mon.name, ac, hp, attacks, "monsters", dex_mod)


def _parse_pc(pc: PC) -> Combatant:
    attacks = [a.dict() for a in pc.attacks]
    return Combatant(pc.name, pc.ac, pc.hp, attacks, "party", 0)


def choose_target(actor: Combatant, enemies: List[Combatant], strategy: str = "lowest_hp", seed: int | None = None) -> Combatant | None:
    """Pick a target from ``enemies`` according to ``strategy``."""
    if not enemies:
        return None
    if strategy == "lowest_hp":
        return min(enemies, key=lambda e: e.hp)
    if strategy == "closest":
        return enemies[0]
    if strategy == "random":
        rng = random.Random(seed)
        return rng.choice(enemies)
    raise ValueError(f"unknown strategy {strategy}")


def run_round(party: List[PC], monsters: List[MonsterSidecar], seed: int | None = None) -> Dict[str, object]:
    """Resolve a single combat round.

    Returns a mapping with ``log`` (list of strings) and ``state`` containing
    updated hit points and defeat flags for all combatants.
    """
    rng = random.Random(seed)
    combatants: List[Combatant] = [_parse_pc(p) for p in party] + [_parse_monster(m) for m in monsters]

    # initiative
    for c in combatants:
        init_seed = rng.randint(0, 10_000_000)
        c.init = roll(f"1d20+{c.dex_mod}", seed=init_seed)["total"]
    combatants.sort(key=lambda c: c.init, reverse=True)

    log: List[str] = []

    for actor in combatants:
        if actor.defeated:
            continue
        enemies = [c for c in combatants if c.side != actor.side and not c.defeated]
        if not enemies:
            break
        target_seed = rng.randint(0, 10_000_000)
        target = choose_target(actor, enemies, seed=target_seed)
        if target is None:
            continue
        attack = actor.attacks[0]
        hit_seed = rng.randint(0, 10_000_000)
        atk = attack_roll(attack["to_hit"], target.ac, hit_seed)
        if atk["hit"]:
            dmg_seed = rng.randint(0, 10_000_000)
            dmg = damage_roll(attack["damage_dice"], dmg_seed)
            target.hp -= dmg["total"]
            log.append(f"{actor.name} hits {target.name} for {dmg['total']}")
            if target.hp <= 0:
                target.defeated = True
                log.append(f"{target.name} is defeated")
        else:
            log.append(f"{actor.name} misses {target.name}")

    state = {
        "party": [c.to_state() for c in combatants if c.side == "party"],
        "monsters": [c.to_state() for c in combatants if c.side == "monsters"],
    }
    return {"log": log, "state": state}
