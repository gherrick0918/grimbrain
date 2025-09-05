from __future__ import annotations
import random
from typing import Dict, List, Optional

from .campaign import CampaignState, party_to_combatants, apply_combat_results
from .bestiary import make_combatant_from_monster, weapon_names_for_monster
from .skirmish import run_skirmish
from .types import Combatant

TABLE = [
    {"name": "Goblins (2)", "enemies": ["Goblin", "Goblin"]},
    {"name": "Ogre", "enemies": ["Ogre"]},
    {"name": "Wolves (3)", "enemies": ["Wolf", "Wolf", "Wolf"]},
]


def roll_overland_encounter(state: CampaignState, rng: random.Random) -> Optional[dict]:
    return rng.choice(TABLE) if rng.randint(1, 20) <= 3 else None


def _enemy_to_combatant(name: str, idx: int) -> Combatant:
    cmb = make_combatant_from_monster(name, team="B", cid=f"E{idx}")
    wp, off = weapon_names_for_monster(name)
    if wp:
        cmb.weapon = wp
    cmb.offhand = off
    return cmb


def run_encounter(state: CampaignState, rng: random.Random, notes: List[str]) -> Dict[str, object]:
    allies_map = party_to_combatants(state)
    table = roll_overland_encounter(state, rng)
    if not table:
        notes.append("No encounter.")
        return {"encounter": None}
    enemies: List[Combatant] = []
    for idx, ename in enumerate(table["enemies"], 1):
        enemies.append(_enemy_to_combatant(ename, idx))
    roster = list(allies_map.values()) + enemies
    res = run_skirmish(roster, seed=rng.randint(1, 999999))
    apply_combat_results(state, allies_map)
    notes.append(f"Encounter: {table['name']}")
    return {"encounter": table["name"], "winner": res.get("winner")}

