from __future__ import annotations
import json
from pathlib import Path
from typing import Optional, Tuple

from .types import Combatant
from ..character import Character

MONSTER_DIR = Path(__file__).resolve().parents[2] / "data" / "monsters"


def _load_monster_blob(name: str) -> dict:
    base = name.lower().replace(" ", "_")
    candidates = [f"{base}.json", f"{name}.json", f"{base}.yaml", f"{base}.yml"]
    for fn in candidates:
        path = MONSTER_DIR / fn
        if path.exists():
            if path.suffix == ".json":
                return json.loads(path.read_text())
            else:
                import yaml
                return yaml.safe_load(path.read_text())
    raise FileNotFoundError(f"Monster not found: {name}")


def _score(mod: int) -> int:
    return mod * 2 + 10


def make_combatant_from_monster(name: str, *, team: str, cid: Optional[str] = None) -> Combatant:
    blob = _load_monster_blob(name)
    cid = cid or blob["name"][0].upper()
    actor = Character(
        str_score=_score(blob["str_mod"]),
        dex_score=_score(blob["dex_mod"]),
        con_score=_score(blob["con_mod"]),
        int_score=_score(blob["int_mod"]),
        wis_score=_score(blob["wis_mod"]),
        cha_score=_score(blob["cha_mod"]),
        proficiency_bonus=blob.get("proficiency_bonus", 2),
        speed_ft=blob.get("speed", 30),
        proficiencies={"simple weapons", "martial weapons"},
    )
    c = Combatant(
        id=cid,
        name=blob["name"],
        team=team,
        actor=actor,
        hp=blob["hp"],
        weapon=blob.get("weapon_primary", ""),
        offhand=blob.get("weapon_offhand"),
        ac=blob["ac"],
        str_mod=blob["str_mod"],
        dex_mod=blob["dex_mod"],
        con_mod=blob["con_mod"],
        int_mod=blob["int_mod"],
        wis_mod=blob["wis_mod"],
        cha_mod=blob["cha_mod"],
        proficiency_bonus=blob.get("proficiency_bonus", 2),
        reach=blob.get("reach", 5),
        speed=blob.get("speed", 30),
        ranged=blob.get("ranged", False),
        proficient_athletics=blob.get("proficient_athletics", False),
        proficient_acrobatics=blob.get("proficient_acrobatics", False),
    )
    return c


def weapon_names_for_monster(name: str) -> Tuple[Optional[str], Optional[str]]:
    blob = _load_monster_blob(name)
    return blob.get("weapon_primary"), blob.get("weapon_offhand")

