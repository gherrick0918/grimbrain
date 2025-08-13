"""Minimal combat round resolution."""
from __future__ import annotations

import random
from typing import Callable, Dict, List
from copy import deepcopy

from .checks import attack_roll, damage_roll, saving_throw
from .dice import roll
from ..models import MonsterSidecar, PC, SpellSidecar, dump_model
from .encounter import compute_encounter


class Combatant:
    """Internal mutable combatant state."""

    def __init__(
        self,
        name: str,
        ac: int,
        hp: int,
        attacks: List[Dict[str, object]],
        side: str,
        dex_mod: int = 0,
    ):
        self.name = name
        self.ac = ac
        self.hp = hp
        self.attacks = attacks
        self.side = side
        self.dex_mod = dex_mod
        self.defeated = False
        # 5e dying rules
        self.downed = False
        self.stable = False
        self.death_successes = 0
        self.death_failures = 0

    def to_state(self) -> Dict[str, object]:
        return {"name": self.name, "hp": self.hp, "defeated": self.defeated}


def _parse_monster(mon: MonsterSidecar, rng: random.Random) -> Combatant:
    ac = int(mon.ac.split()[0])
    hp_str = mon.hp
    if "(" in hp_str and ")" in hp_str:
        expr = hp_str.split("(")[1].split(")")[0]
        seed = rng.randint(0, 10_000_000)
        hp = roll(expr, seed=seed)["total"]
    else:
        hp = int(hp_str.split()[0])
    dex_mod = (mon.dex - 10) // 2
    attacks: List[Dict[str, object]] = []
    for a in mon.actions_struct:
        attacks.append({"to_hit": a.attack_bonus, "damage_dice": a.damage_dice, "type": a.type})
    return Combatant(mon.name, ac, hp, attacks, "monsters", dex_mod)


def _parse_pc(pc: PC) -> Combatant:
    attacks = [dump_model(a) for a in pc.attacks]
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
    combatants: List[Combatant] = [_parse_pc(p) for p in party] + [
        _parse_monster(m, rng) for m in monsters
    ]

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


def run_encounter(
    party: List[PC],
    monsters: List[MonsterSidecar],
    seed: int | None = None,
    max_rounds: int = 10,
) -> Dict[str, object]:
    """Run combat until one side is defeated or ``max_rounds`` reached."""
    rng = random.Random(seed)
    combatants: List[Combatant] = [_parse_pc(p) for p in party] + [
        _parse_monster(m, rng) for m in monsters
    ]

    # initiative once
    for c in combatants:
        init_seed = rng.randint(0, 10_000_000)
        c.init = roll(f"1d20+{c.dex_mod}", seed=init_seed)["total"]
        c.concentrating: str | None = None
    combatants.sort(key=lambda c: c.init, reverse=True)

    log: List[str] = []
    rounds = 0

    party_alive = any(c.side == "party" and not c.defeated for c in combatants)
    monsters_alive = any(c.side == "monsters" and not c.defeated for c in combatants)

    while rounds < max_rounds and party_alive and monsters_alive:
        rounds += 1
        for actor in combatants:
            if actor.defeated:
                continue
            enemies = [c for c in combatants if c.side != actor.side and not c.defeated]
            if not enemies:
                break
            attack = actor.attacks[0]
            if attack.get("save_dc"):
                dmg_seed = rng.randint(0, 10_000_000)
                dmg_total = damage_roll(attack["damage_dice"], dmg_seed)["total"]
                ability = attack.get("save_ability", "dex")
                for target in enemies:
                    save_seed = rng.randint(0, 10_000_000)
                    mod = getattr(target, f"{ability}_mod", 0)
                    save = saving_throw(attack["save_dc"], mod, seed=save_seed)
                    taken = dmg_total if not save["success"] else dmg_total // 2
                    target.hp -= taken
                    log.append(
                        f"{actor.name}'s {attack['name']} hits {target.name} for {taken}"
                    )
                    if target.hp <= 0:
                        target.defeated = True
                        log.append(f"{target.name} is defeated")
                if attack.get("concentration"):
                    actor.concentrating = attack["name"]
            else:
                enemies_alive = [c for c in enemies if not c.defeated]
                if not enemies_alive:
                    break
                target_seed = rng.randint(0, 10_000_000)
                target = choose_target(actor, enemies_alive, seed=target_seed)
                if target is None:
                    continue
                hit_seed = rng.randint(0, 10_000_000)
                atk = attack_roll(attack.get("to_hit", 0), target.ac, hit_seed)
                if atk["hit"]:
                    dmg_seed = rng.randint(0, 10_000_000)
                    dmg = damage_roll(attack["damage_dice"], dmg_seed)
                    target.hp -= dmg["total"]
                    log.append(
                        f"{actor.name} hits {target.name} for {dmg['total']}"
                    )
                    if target.hp <= 0:
                        target.defeated = True
                        log.append(f"{target.name} is defeated")
                else:
                    log.append(f"{actor.name} misses {target.name}")
        party_alive = any(
            c.side == "party" and not c.defeated for c in combatants
        )
        monsters_alive = any(
            c.side == "monsters" and not c.defeated for c in combatants
        )
        if not party_alive or not monsters_alive:
            break

    winner = (
        "party" if party_alive and not monsters_alive else "monsters" if monsters_alive and not party_alive else "none"
    )

    state = {
        "party": [c.to_state() for c in combatants if c.side == "party"],
        "monsters": [c.to_state() for c in combatants if c.side == "monsters"],
    }

    xp = compute_encounter(monsters)
    summary = {"winner": winner, "rounds": rounds, "xp": xp["total_xp"], "drops": []}
    return {"log": log, "state": state, "rounds": rounds, "winner": winner, "summary": summary}


def parse_monster_spec(spec: str, lookup: Callable[[str], MonsterSidecar]) -> List[MonsterSidecar]:
    """Expand ``spec`` like ``'goblin x3, goblin boss'`` into sidecars."""
    monsters: List[MonsterSidecar] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        count = 1
        if "x" in part:
            name_part, mult = part.rsplit("x", 1)
            try:
                count = int(mult.strip())
                part = name_part.strip()
            except ValueError:
                part = part
        base = lookup(part)
        for _ in range(count):
            monsters.append(deepcopy(base))
    return monsters
