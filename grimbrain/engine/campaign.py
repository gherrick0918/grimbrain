from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
import json
import yaml

from ..models import PC, MonsterSidecar
from .combat import run_encounter as _run_encounter
from .encounter import apply_difficulty
from ..campaign import load_party_file
from ..retrieval.query_router import run_query


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
    encounter: str | dict | None = None
    on_victory: Optional[str] = None
    on_defeat: Optional[str] = None
    rest: Optional[str] = None
    check: Optional[Check] = None
    choices: List[Choice] = field(default_factory=list)


@dataclass
class Campaign:
    name: str
    party_files: List[str]
    scenes: Dict[str, Scene]
    start: str
    seed: Optional[int] = None


def load_yaml_campaign(path: str | Path) -> Campaign:
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
            rest=sdata.get("rest"),
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


def run_campaign_encounter(
    pcs: List[PC],
    enemy_name: str,
    seed: int | None = None,
    max_rounds: int = 10,
    difficulty: str = "normal",
    scale: bool = False,
) -> Dict[str, object]:
    _, data, _ = run_query(enemy_name, "monster")
    if not data:
        raise ValueError(f"Monster '{enemy_name}' not found in index")
    mon = MonsterSidecar(**data)
    apply_difficulty([mon], difficulty, scale, len(pcs))
    res = _run_encounter(pcs, [mon], seed=seed, max_rounds=max_rounds)
    outcome = "victory" if res["winner"] == "party" else "defeat"
    hp = {c["name"]: c["hp"] for c in res["state"]["party"]}
    summary = f"{outcome} in {res['rounds']} rounds"
    return {"result": outcome, "summary": summary, "hp": hp}


# --- Lightweight campaign state utilities (PR41) ---
from dataclasses import asdict


@dataclass
class PartyMemberRef:
    id: str
    name: str
    str_mod: int
    dex_mod: int
    con_mod: int
    int_mod: int
    wis_mod: int
    cha_mod: int
    ac: int
    max_hp: int
    pb: int
    speed: int
    xp: int = 0
    level: int = 1
    reach: int = 5
    ranged: bool = False
    prof_athletics: bool = False
    prof_acrobatics: bool = False
    weapon_primary: Optional[str] = None
    weapon_offhand: Optional[str] = None


@dataclass
class QuestLogItem:
    id: str
    text: str
    done: bool = False


@dataclass
class CampaignState:
    seed: int
    day: int = 1
    time_of_day: str = "morning"
    location: str = "Wilderness"
    gold: int = 0
    inventory: Dict[str, int] = field(default_factory=dict)
    party: List[PartyMemberRef] = field(default_factory=list)
    current_hp: Dict[str, int] = field(default_factory=dict)
    quest_log: List[QuestLogItem] = field(default_factory=list)
    last_long_rest_day: int = 0
    # PR 44a: base encounter chance percent (0–100). Default 30%.
    encounter_chance: int = 30
    # PR 44b: encounter clock that ramps chance until an encounter happens
    encounter_clock: int = 0  # additive percent
    encounter_clock_step: int = 10  # how much to add after each no-encounter


def load_campaign(path: str) -> CampaignState:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    party = [PartyMemberRef(**p) for p in raw.get("party", [])]
    quests = [QuestLogItem(**q) for q in raw.get("quest_log", [])]
    st = CampaignState(
        seed=raw["seed"],
        day=raw.get("day", 1),
        time_of_day=raw.get("time_of_day", "morning"),
        location=raw.get("location", "Wilderness"),
        gold=raw.get("gold", 0),
        inventory=raw.get("inventory", {}),
        party=party,
        current_hp=raw.get("current_hp", {}),
        quest_log=quests,
        last_long_rest_day=raw.get("last_long_rest_day", 0),
        encounter_chance=raw.get("encounter_chance", 30),
        encounter_clock=raw.get("encounter_clock", 0),
        encounter_clock_step=raw.get("encounter_clock_step", 10),
    )
    if not st.current_hp:
        for p in st.party:
            st.current_hp[p.id] = p.max_hp
    return st


def save_campaign(state: CampaignState, path: str) -> None:
    blob = asdict(state)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(blob, f, indent=2)


def advance_time(state: CampaignState, hours: int = 4) -> None:
    order = ["morning", "afternoon", "evening", "night"]
    idx = order.index(state.time_of_day)
    steps = max(1, hours // 4)
    idx2 = (idx + steps) % 4
    if idx == 3 and idx2 == 0:
        state.day += 1
    state.time_of_day = order[idx2]


def party_to_combatants(state: CampaignState) -> Dict[str, Combatant]:
    from .util import make_combatant_from_party_member

    res: Dict[str, Combatant] = {}
    for p in state.party:
        c = make_combatant_from_party_member(p, team="A", cid=p.id)
        c.hp = state.current_hp.get(p.id, p.max_hp)
        c.max_hp = p.max_hp
        res[p.id] = c
    return res


def apply_combat_results(state: CampaignState, roster: Dict[str, Combatant]) -> None:
    for cid, cmb in roster.items():
        state.current_hp[cid] = max(0, cmb.hp)

