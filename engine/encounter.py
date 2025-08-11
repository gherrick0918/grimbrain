from typing import List
from models import MonsterSidecar

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
