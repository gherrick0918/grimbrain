from typing import List
from ..models import MonsterSidecar

XP_BY_NAME = {
    "goblin": 50,
    "goblin boss": 200,
}

MULTIPLIERS = [
    (1, 1),
    (2, 1.5),
    (6, 2),
    (10, 2.5),
    (14, 3),
    (float("inf"), 4),
]

BANDS = {
    1: "1",
    2: "2",
    3: "3-6",
    4: "7-10",
    5: "11-14",
    6: "15+",
}


def _band_for_count(count: int) -> tuple[str, float]:
    for i, (limit, mult) in enumerate(MULTIPLIERS, start=1):
        if count <= limit:
            return BANDS[i], mult
    return BANDS[6], 4


def compute_encounter(monsters: List[MonsterSidecar]) -> dict:
    count = len(monsters)
    total = 0
    for m in monsters:
        total += XP_BY_NAME.get(m.name.lower(), 0)
    band, mult = _band_for_count(count)
    adjusted = int(total * mult)
    return {"total_xp": total, "adjusted_xp": adjusted, "band": band}


def apply_difficulty(
    monsters: List[MonsterSidecar],
    difficulty: str = "normal",
    scale: bool = False,
    party_size: int = 1,
) -> dict:
    """Apply difficulty and scaling modifiers to monsters."""
    hp_mult = 1.0
    to_hit = 0
    if difficulty == "easy":
        hp_mult *= 0.85
        to_hit -= 1
    elif difficulty == "hard":
        hp_mult *= 1.15
        to_hit += 1
    if scale:
        mult = 0.9 + 0.05 * (party_size - 2)
        mult = max(0.8, min(1.2, mult))
        hp_mult *= mult
    for m in monsters:
        try:
            base = int(m.hp.split()[0])
            m.hp = str(int(round(base * hp_mult)))
        except Exception:
            pass
        for a in m.actions_struct:
            a.attack_bonus += to_hit
    return {"hp_mult": hp_mult, "to_hit": to_hit}
