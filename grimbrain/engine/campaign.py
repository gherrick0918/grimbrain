from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
import json
import yaml

from ..models import PC, MonsterSidecar
from ..fallback_monsters import FALLBACK_MONSTERS
from .combat import run_encounter as _run_encounter
from ..campaign import load_party_file


@dataclass
class Choice:
    text: str
    next: str


@dataclass
class Check:
    ability: Optional[str] = None
    skill: Optional[str] = None
    dc: int = 10
    advantage: bool = False
    on_success: Optional[str] = None
    on_failure: Optional[str] = None


@dataclass
class Scene:
    id: str
    text: str
    encounter: Optional[str] = None
    on_victory: Optional[str] = None
    on_defeat: Optional[str] = None
    check: Optional[Check] = None
    choices: List[Choice] = field(default_factory=list)


@dataclass
class Campaign:
    name: str
    party_files: List[str]
    scenes: Dict[str, Scene]
    start: str
    seed: Optional[int] = None


def load_campaign(path: str | Path) -> Campaign:
    p = Path(path)
    if p.is_dir():
        data = yaml.safe_load((p / "campaign.yaml").read_text())
    else:
        data = yaml.safe_load(p.read_text())
        p = p.parent
    scenes: Dict[str, Scene] = {}
    raw_scenes = data.get("scenes", {})
    for sid, sdata in raw_scenes.items():
        choices: List[Choice] = []
        for c in sdata.get("choices", []):
            c_map = dict(c)
            if "label" in c_map and "text" not in c_map:
                c_map["text"] = c_map.pop("label")
            if "goto" in c_map and "next" not in c_map:
                c_map["next"] = c_map.pop("goto")
            choices.append(Choice(**c_map))
        check = Check(**sdata["check"]) if "check" in sdata else None
        scenes[sid] = Scene(
            id=sid,
            text=sdata.get("text", ""),
            encounter=sdata.get("encounter"),
            on_victory=sdata.get("on_victory"),
            on_defeat=sdata.get("on_defeat"),
            check=check,
            choices=choices,
        )
    start = data.get("start") or next(iter(scenes))
    camp = Campaign(
        name=data.get("name") or data.get("title", "Unnamed"),
        party_files=data.get("party_files", []),
        scenes=scenes,
        start=start,
        seed=data.get("seed"),
    )
    return camp


def load_party(camp: Campaign, base: Path) -> List[PC]:
    pcs: List[PC] = []
    for pf in camp.party_files:
        pcs.extend(load_party_file(base / pf))
    return pcs


def run_encounter(
    pcs: List[PC],
    enemy_name: str,
    seed: int | None = None,
    max_rounds: int = 10,
) -> Dict[str, object]:
    data = FALLBACK_MONSTERS[enemy_name.lower()]
    mon = MonsterSidecar(**data)
    res = _run_encounter(pcs, [mon], seed=seed, max_rounds=max_rounds)
    outcome = "victory" if res["winner"] == "party" else "defeat"
    hp = {c["name"]: c["hp"] for c in res["state"]["party"]}
    summary = f"{outcome} in {res['rounds']} rounds"
    return {"result": outcome, "summary": summary, "hp": hp}
