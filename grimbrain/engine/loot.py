
from typing import Dict, List
import random


def roll_loot(enemies: List[str], rng: random.Random, notes: List[str]) -> Dict[str, int]:
    names = " ".join(n.lower() for n in enemies)
    hard = "ogre" in names
    gold = ((rng.randint(1, 6) + rng.randint(1, 6)) * 10) if hard else rng.randint(1, 6) * 5
    inv: Dict[str, int] = {}
    if rng.random() < 0.5:
        inv["potion_healing"] = inv.get("potion_healing", 0) + 1
    if rng.random() < 0.25:
        inv["ammo_arrows"] = inv.get("ammo_arrows", 0) + 20
    notes.append(f"Loot: +{gold} gp, items={inv or {}}")
    return {"gold": gold, **inv}
