from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Tuple
import random
from pathlib import Path

from .types import Combatant, Target
from .round import roll_initiative   # reuse your initiative helper
from ..codex.weapons import WeaponIndex
from ..codex.armor import ArmorIndex
from ..rules.defense import compute_ac
from ..rules.attacks import can_two_weapon
from .combat import resolve_attack


def _reach_ft(weapon) -> int:
    return 10 if weapon.has_prop("reach") else 5


def _speed(cmb: Combatant) -> int:
    return getattr(cmb.actor, "speed_ft", 30)


def _ac_for(defender: Combatant, armor_idx: ArmorIndex) -> int:
    return int(compute_ac(defender.actor, armor_idx)["ac"])


def _move_toward(dist: int, feet: int) -> int:
    return max(0, dist - max(0, feet))


def _move_away(dist: int, feet: int) -> int:
    return dist + max(0, feet)


@dataclass
class SceneResult:
    winner: str
    rounds: int
    log: List[str]
    final_distance_ft: int
    a_hp: int
    b_hp: int


def _take_scene_turn(attacker: Combatant, defender: Combatant, *,
                     weapon_idx: WeaponIndex, armor_idx: ArmorIndex,
                     rng: random.Random, distance_ft: int) -> Tuple[List[str], int, bool]:
    """
    Returns (log, new_distance_ft, defender_dropped)
    """
    log: List[str] = []
    speed = _speed(attacker)
    w_main = weapon_idx.get(attacker.weapon)
    reach = _reach_ft(w_main)

    # Decide movement
    new_dist = distance_ft
    performed_action = False
    used_loading_this_turn = False

    # Simple policies
    if w_main.kind == "melee":
        if new_dist > reach:
            gap = new_dist - reach
            if gap > speed:
                # Dash to reach if possible this turn, otherwise dash full 2*speed
                dash_step = min(speed * 2, gap)
                new_dist2 = _move_toward(new_dist, dash_step)
                log.append(f"{attacker.name} dashes: {new_dist}ft -> {new_dist2}ft")
                new_dist = new_dist2
                # dashed: no attack this turn
                return (log, new_dist, False)
            else:
                step = min(speed, gap)
                new_dist2 = _move_toward(new_dist, step)
                log.append(f"{attacker.name} moves: {new_dist}ft -> {new_dist2}ft")
                new_dist = new_dist2
        # Attack if in reach
        if new_dist <= reach:
            res = resolve_attack(
                attacker.actor, attacker.weapon,
                Target(ac=_ac_for(defender, armor_idx), hp=defender.hp, cover=defender.cover, distance_ft=new_dist),
                weapon_idx, base_mode="none", power=False, offhand=False, two_handed=False,
                has_fired_loading_weapon_this_turn=False, rng=rng
            )
            if not res["ok"]:
                log.append(f"{attacker.name} cannot attack: {res['reason']}")
            else:
                tag = "CRIT" if res["is_crit"] else ("HIT" if res["is_hit"] else "MISS")
                log.append(f"{attacker.name} attacks with {res['weapon']} @ {new_dist}ft => {tag}")
                log.append(f"  damage {res['damage_string']}: rolls={res['damage']['rolls']} total={res['damage']['total']}")
                if res["spent_ammo"]:
                    log.append("  ammo: spent 1")
                defender.hp -= int(res["damage"]["total"])
                performed_action = True
                if w_main.has_prop("loading"):
                    used_loading_this_turn = True
                if defender.hp <= 0:
                    log.append(f"{defender.name} drops to 0 HP!")
                    return (log, new_dist, True)
        # Optional off-hand if applicable and still alive/in reach
        if defender.hp > 0 and attacker.offhand:
            w_off = weapon_idx.get(attacker.offhand)
            if can_two_weapon(w_off) and new_dist <= _reach_ft(w_off):
                res = resolve_attack(
                    attacker.actor, attacker.offhand,
                    Target(ac=_ac_for(defender, armor_idx), hp=defender.hp, cover=defender.cover, distance_ft=new_dist),
                    weapon_idx, base_mode="none", power=False, offhand=True, two_handed=False,
                    has_fired_loading_weapon_this_turn=used_loading_this_turn, rng=rng
                )
                if res["ok"]:
                    tag = "CRIT" if res["is_crit"] else ("HIT" if res["is_hit"] else "MISS")
                    log.append(f"  Off-hand {res['weapon']} => {tag}")
                    log.append(f"    damage {res['damage_string']}: rolls={res['damage']['rolls']} total={res['damage']['total']}")
                    defender.hp -= int(res["damage"]["total"])
                    if defender.hp <= 0:
                        log.append(f"{defender.name} drops to 0 HP!")
                        return (log, new_dist, True)
        return (log, new_dist, False)

    # Ranged logic (kite)
    KITE = 30  # desired standoff distance
    if new_dist <= 5:
        # Disengage and step back, then shoot
        step = min(speed, KITE - new_dist if KITE > new_dist else speed)
        new_dist = _move_away(new_dist, step)
        log.append(f"{attacker.name} disengages and moves: {distance_ft}ft -> {new_dist}ft")
        res = resolve_attack(
            attacker.actor,
            attacker.weapon,
            Target(
                ac=_ac_for(defender, armor_idx),
                hp=defender.hp,
                cover=defender.cover,
                distance_ft=new_dist,
            ),
            weapon_idx,
            base_mode="none",
            power=False,
            offhand=False,
            two_handed=False,
            has_fired_loading_weapon_this_turn=False,
            rng=rng,
        )
        if not res["ok"]:
            log.append(f"{attacker.name} cannot attack: {res['reason']}")
            return (log, new_dist, False)
        tag = "CRIT" if res["is_crit"] else ("HIT" if res["is_hit"] else "MISS")
        log.append(f"{attacker.name} shoots with {res['weapon']} @ {new_dist}ft => {tag}")
        log.append(
            f"  damage {res['damage_string']}: rolls={res['damage']['rolls']} total={res['damage']['total']}"
        )
        if res["spent_ammo"]:
            log.append("  ammo: spent 1")
        defender.hp -= int(res["damage"]["total"])
        if defender.hp <= 0:
            log.append(f"{defender.name} drops to 0 HP!")
            return (log, new_dist, True)
        return (log, new_dist, False)
    else:
        # Step back toward kite distance (free move), then shoot
        if new_dist < KITE:
            gap = KITE - new_dist
            if gap > speed:
                dash_step = min(speed * 2, gap)
                new_dist2 = _move_away(new_dist, dash_step)
                log.append(f"{attacker.name} dashes: {new_dist}ft -> {new_dist2}ft")
                new_dist = new_dist2
                # dashed: no attack this turn
                return (log, new_dist, False)
            else:
                step = min(speed, gap)
                new_dist2 = _move_away(new_dist, step)
                log.append(f"{attacker.name} moves: {new_dist}ft -> {new_dist2}ft")
                new_dist = new_dist2
        res = resolve_attack(
            attacker.actor, attacker.weapon,
            Target(ac=_ac_for(defender, armor_idx), hp=defender.hp, cover=defender.cover, distance_ft=new_dist),
            weapon_idx, base_mode="none", power=False, offhand=False, two_handed=False,
            has_fired_loading_weapon_this_turn=False, rng=rng
        )
        if not res["ok"]:
            log.append(f"{attacker.name} cannot attack: {res['reason']}")
            return (log, new_dist, False)
        tag = "CRIT" if res["is_crit"] else ("HIT" if res["is_hit"] else "MISS")
        log.append(f"{attacker.name} shoots with {res['weapon']} @ {new_dist}ft => {tag}")
        log.append(f"  damage {res['damage_string']}: rolls={res['damage']['rolls']} total={res['damage']['total']}")
        if res["spent_ammo"]:
            log.append("  ammo: spent 1")
        defender.hp -= int(res["damage"]["total"])
        if defender.hp <= 0:
            log.append(f"{defender.name} drops to 0 HP!")
            return (log, new_dist, True)
        return (log, new_dist, False)


def run_scene(a: Combatant, b: Combatant, *, seed: int = 42, max_rounds: int = 20, start_distance_ft: int = 30) -> SceneResult:
    rng = random.Random(seed)
    widx = WeaponIndex.load(Path("data/weapons.json"))
    aidx = ArmorIndex.load(Path("data/armor.json"))

    first, second, init = roll_initiative(a, b, rng)
    distance = start_distance_ft
    log: List[str] = [f"Initiative — {first.name} vs {second.name}: {init['A']} to {init['B']}", f"Start distance: {distance}ft"]
    round_no = 1

    while a.hp > 0 and b.hp > 0 and round_no <= max_rounds:
        log.append(f"— Round {round_no} —")
        # First acts
        tlog, distance, down = _take_scene_turn(first, second, weapon_idx=widx, armor_idx=aidx, rng=rng, distance_ft=distance)
        log.extend(tlog)
        if down:
            break
        # Second acts
        tlog, distance, down = _take_scene_turn(second, first, weapon_idx=widx, armor_idx=aidx, rng=rng, distance_ft=distance)
        log.extend(tlog)
        if down:
            break
        round_no += 1

    winner = first.name if second.hp <= 0 else (second.name if first.hp <= 0 else "none")
    return SceneResult(winner=winner, rounds=round_no if winner != "none" else max_rounds, log=log,
                       final_distance_ft=distance, a_hp=a.hp, b_hp=b.hp)

