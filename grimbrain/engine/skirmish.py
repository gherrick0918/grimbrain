from __future__ import annotations
from typing import List, Dict, Tuple
import random
from pathlib import Path

from .types import Combatant
from .scene import _take_scene_turn, _maybe_opportunity_attack
from ..codex.weapons import WeaponIndex
from ..codex.armor import ArmorIndex


def _init_mod(c: Combatant) -> int:
    return (c.actor.dex_score - 10) // 2


def roll_initiative_order(roster: List[Combatant], rng: random.Random) -> List[Tuple[int, Combatant]]:
    order: List[Tuple[int, Combatant]] = []
    for c in roster:
        d = rng.randint(1, 20)
        order.append((d + _init_mod(c), c))
    order.sort(key=lambda t: (-t[0], t[1].name))
    return order


def _alive(c: Combatant) -> bool:
    return (c.hp > 0) and (not getattr(c.death, "dead", False))


def _living_team(roster: List[Combatant], team: str) -> List[Combatant]:
    return [c for c in roster if c.team == team and _alive(c)]


def _enemies_of(roster: List[Combatant], team: str) -> List[Combatant]:
    return [c for c in roster if c.team != team and _alive(c)]


def _closest_enemy(me: Combatant, enemies: List[Combatant]) -> Combatant | None:
    if not enemies:
        return None
    me_dist = me.distance_ft or 30
    return min(enemies, key=lambda e: (abs((e.distance_ft or 30) - me_dist), e.hp, e.name))


def run_skirmish(roster: List[Combatant], *, seed: int = 42, start_distance_ft: int = 30, max_rounds: int = 20) -> Dict[str, object]:
    """
    Multi-combatant wrapper that iterates round/turns and reuses scene per-turn logic.
    All combatants share a single scalar distance between "front lines"; simple but effective for 1-D fights.
    """
    rng = random.Random(seed)
    widx = WeaponIndex.load(Path("data/weapons.json"))
    aidx = ArmorIndex.load(Path("data/armor.json"))

    for c in roster:
        c.distance_ft = start_distance_ft
        c.reaction_available = True

    log: List[str] = []
    round_no = 1

    def teams_alive() -> List[str]:
        return sorted({c.team for c in roster if _alive(c)})

    order = roll_initiative_order(roster, rng)
    log.append("Initiative:")
    log.extend([f"  {c.name} ({c.team}) {score}" for score, c in order])
    log.append(f"Start distance: {start_distance_ft}ft")

    while round_no <= max_rounds and len(teams_alive()) > 1:
        log.append(f"— Round {round_no} —")
        for c in roster:
            c.reaction_available = True

        for _, actor in order:
            if not _alive(actor):
                continue
            enemies = _enemies_of(roster, actor.team)
            if not enemies:
                break
            target = _closest_enemy(actor, enemies) or enemies[0]
            prev_dist = actor.distance_ft or start_distance_ft
            tlog, new_dist, _ = _take_scene_turn(
                actor,
                target,
                weapon_idx=widx,
                armor_idx=aidx,
                rng=rng,
                distance_ft=prev_dist,
            )
            log.extend([f"{actor.name} ({actor.team}) turn:"] + tlog)
            used_disengage = any("disengage" in line.lower() for line in tlog)
            if new_dist > prev_dist:
                for e in enemies:
                    if e is target:
                        continue
                    log.extend(
                        _maybe_opportunity_attack(
                            e,
                            actor,
                            prev_dist=prev_dist,
                            new_dist=new_dist,
                            used_disengage=used_disengage,
                            weapon_idx=widx,
                            armor_idx=aidx,
                            rng=rng,
                        )
                    )
            for c in roster:
                c.distance_ft = new_dist
            if len(teams_alive()) <= 1:
                break

        round_no += 1

    alive_teams = teams_alive()
    winner = alive_teams[0] if len(alive_teams) == 1 else "none"
    team_hp: Dict[str, int] = {}
    for c in roster:
        team_hp[c.team] = team_hp.get(c.team, 0) + max(0, c.hp)

    return {"winner": winner, "rounds": round_no - 1 if winner != "none" else max_rounds, "log": log, "team_hp": team_hp}
