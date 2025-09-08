from typing import Dict, List
import random

XP_THRESHOLDS = {2: 300, 3: 900, 4: 2700, 5: 6500}


def proficiency_bonus_for_level(level: int) -> int:
    if level >= 17:
        return 6
    if level >= 13:
        return 5
    if level >= 9:
        return 4
    if level >= 5:
        return 3
    return 2


def xp_value_for_enemy(name: str) -> int:
    n = name.lower()
    if "ogre" in n:
        return 450
    if "orc" in n:
        return 100
    # goblin, wolf, skeleton, bandit baseline
    return 50


def award_xp(enemies: List[str], pcs: List[dict], notes: List[str]) -> Dict[str, int]:
    total = sum(xp_value_for_enemy(n) for n in enemies)
    living = [pc for pc in pcs if pc.get("hp", pc.get("max_hp", 0)) > 0]
    share = total // max(1, len(living))
    gains: Dict[str, int] = {}
    for pc in pcs:
        pid = pc.get("id") or pc.get("name")
        if pc in living:
            pc["xp"] = pc.get("xp", 0) + share
            gains[pid] = share
    # Use ASCII arrow to avoid encoding issues on some platforms
    notes.append(
        f"XP awarded: {total} total -> {share} each to {len(living)} PC(s)."
    )
    return gains


def maybe_level_up(pc: dict, rng: random.Random, notes: List[str]) -> bool:
    leveled = False
    while True:
        cur = pc.get("level", 1)
        nxt = cur + 1
        thresh = XP_THRESHOLDS.get(nxt)
        if not thresh or pc.get("xp", 0) < thresh:
            break
        pc["level"] = nxt
        roll = max(1, rng.randint(1, 10) + pc.get("con_mod", 0))
        pc["max_hp"] = pc.get("max_hp", 1) + roll
        pc["hp"] = pc["max_hp"]
        pb = proficiency_bonus_for_level(nxt)
        pc["pb"] = pb
        pc["prof"] = pb
        notes.append(
            f"{pc.get('name', 'PC')} reaches level {nxt}! +{roll} HP (max {pc['max_hp']}), PB now {pb}."
        )
        leveled = True
    return leveled
