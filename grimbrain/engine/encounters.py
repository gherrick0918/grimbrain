from __future__ import annotations

import random
from typing import Dict, List, Optional

from .bestiary import make_combatant_from_monster, weapon_names_for_monster
from .campaign import CampaignState, apply_combat_results, party_to_combatants
from .loot import roll_loot
from .progression import award_xp, maybe_level_up
from .skirmish import run_skirmish
from .types import Combatant

TABLE = [
    {"name": "Goblins (2)", "enemies": ["Goblin", "Goblin"]},
    {"name": "Ogre", "enemies": ["Ogre"]},
    {"name": "Wolves (3)", "enemies": ["Wolf", "Wolf", "Wolf"]},
]


def roll_overland_encounter(state: CampaignState, rng: random.Random) -> Optional[dict]:
    """Roll for an overland encounter using the state's configured chance."""
    # PR 44a/44b: effective chance = base + clock (capped 0..100)
    base = max(0, min(100, getattr(state, "encounter_chance", 30)))
    clock = max(0, getattr(state, "encounter_clock", 0))
    chance = min(100, base + clock)
    if rng.randint(1, 100) <= chance:
        return rng.choice(TABLE)
    return None


def _enemy_to_combatant(name: str, idx: int) -> Combatant:
    cmb = make_combatant_from_monster(name, team="B", cid=f"E{idx}")
    wp, off = weapon_names_for_monster(name)
    if wp:
        cmb.weapon = wp
    cmb.offhand = off
    return cmb


def run_encounter(
    state: CampaignState, rng: random.Random, notes: List[str], force: bool = False
) -> Dict[str, object]:
    allies_map = party_to_combatants(state)
    table = roll_overland_encounter(state, rng) if not force else rng.choice(TABLE)
    if not table:
        notes.append("No encounter.")
        return {"encounter": None}
    enemies: List[Combatant] = []
    for idx, ename in enumerate(table["enemies"], 1):
        cmb = _enemy_to_combatant(ename, idx)
        cmb.environment_light = getattr(state, "light_level", "normal")
        enemies.append(cmb)
    roster = list(allies_map.values()) + enemies
    res = run_skirmish(roster, seed=rng.randint(1, 999999))
    apply_combat_results(state, allies_map)

    winner = res.get("winner")
    loot: Dict[str, int] = {}
    if winner == "A":
        pcs_data = []
        for p in state.party:
            pdata = {
                "id": p.id,
                "name": p.name,
                "xp": p.xp,
                "level": p.level,
                "max_hp": p.max_hp,
                "con_mod": p.con_mod,
                "pb": p.pb,
                "hp": state.current_hp.get(p.id, p.max_hp),
            }
            pcs_data.append((p, pdata))

        award_xp(table["enemies"], [d for _, d in pcs_data], notes)

        for p, pdata in pcs_data:
            p.xp = pdata["xp"]

        for p, pdata in pcs_data:
            if maybe_level_up(pdata, rng, notes):
                p.level = pdata["level"]
                p.max_hp = pdata["max_hp"]
                p.pb = pdata["pb"]
                state.current_hp[p.id] = pdata["hp"]

        loot = roll_loot(table["enemies"], rng, notes)
        state.gold += loot.get("gold", 0)
        for item, qty in loot.items():
            if item == "gold":
                continue
            state.inventory[item] = state.inventory.get(item, 0) + qty

    return {
        "encounter": table["name"],
        "winner": winner,
        "loot": loot,
        "rounds": res.get("rounds"),
    }
