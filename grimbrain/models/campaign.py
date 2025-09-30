from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Quest(BaseModel):
    id: str
    title: str
    steps: List[str] = []


class Campaign(BaseModel):
    name: str = Field(min_length=1)
    party: List[str]
    packs: List[str] = []
    quests: List[Quest] = []


@dataclass
class PartyMemberRef:
    id: str
    name: str
    class_: Optional[str] = None
    level: Optional[int] = None
    str_mod: int = 0
    dex_mod: int = 0
    con_mod: int = 0
    int_mod: int = 0
    wis_mod: int = 0
    cha_mod: int = 0
    ac: int = 10
    max_hp: int = 10
    pb: int = 2
    speed: int = 30
    xp: Optional[int] = None
    reach: Optional[int] = None
    ranged: Optional[bool] = None
    prof_athletics: Optional[bool] = None
    prof_acrobatics: Optional[bool] = None
    weapon_primary: Optional[str] = None
    weapon_offhand: Optional[str] = None
    armor: Optional[str] = None
    shield: Optional[bool] = None
    stealth_disadv: Optional[bool] = None
    prof_skills: Optional[List[str]] = None
    prof_saves: Optional[List[str]] = None
    race: Optional[str] = None
    background: Optional[str] = None
    languages: Optional[List[str]] = None
    tool_profs: Optional[List[str]] = None
    features: Optional[Dict[str, Any]] = None
    light_emitter: Optional[bool] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "PartyMemberRef":
        data = dict(d or {})
        hp_info = data.pop("hp", {}) or {}
        max_hp = hp_info.get("max", data.pop("max_hp", None))
        if max_hp is None:
            max_hp_val = 10
        else:
            try:
                max_hp_val = int(max_hp)
            except (TypeError, ValueError):
                max_hp_val = 10
        class_value = data.pop("class", None)
        class_alt = data.pop("class_", None)
        class_name = class_value or class_alt
        level_raw = data.pop("level", None)
        try:
            level_val = int(level_raw) if level_raw is not None else None
        except (TypeError, ValueError):
            level_val = None
        def _coerce_int(key: str, default: int = 0) -> int:
            value = data.pop(key, None)
            try:
                return int(value)
            except (TypeError, ValueError):
                return default
        str_mod = _coerce_int("str_mod")
        dex_mod = _coerce_int("dex_mod")
        con_mod = _coerce_int("con_mod")
        int_mod = _coerce_int("int_mod")
        wis_mod = _coerce_int("wis_mod")
        cha_mod = _coerce_int("cha_mod")
        ac = _coerce_int("ac", 10)
        pb = _coerce_int("pb", 2)
        speed = _coerce_int("speed", 30)
        xp_raw = data.pop("xp", None)
        try:
            xp_val = int(xp_raw) if xp_raw is not None else None
        except (TypeError, ValueError):
            xp_val = None
        reach_raw = data.pop("reach", None)
        try:
            reach_val = int(reach_raw) if reach_raw is not None else None
        except (TypeError, ValueError):
            reach_val = None
        bool_keys = {
            "ranged",
            "prof_athletics",
            "prof_acrobatics",
            "shield",
            "stealth_disadv",
            "light_emitter",
        }
        bool_values: Dict[str, Optional[bool]] = {}
        for key in bool_keys:
            if key in data:
                value = data.pop(key)
                if isinstance(value, str):
                    bool_values[key] = value.strip().lower() in {
                        "1",
                        "true",
                        "yes",
                        "on",
                        "y",
                    }
                else:
                    bool_values[key] = bool(value)
        list_keys = {"prof_skills", "prof_saves", "languages", "tool_profs"}
        list_values: Dict[str, Optional[List[str]]] = {}
        for key in list_keys:
            if key in data:
                value = data.pop(key)
                if value is None:
                    list_values[key] = None
                elif isinstance(value, list):
                    list_values[key] = value
                else:
                    list_values[key] = [str(value)]
        features_value = data.pop("features", None)
        known_keys = {
            "id",
            "name",
            "weapon_primary",
            "weapon_offhand",
            "armor",
            "race",
            "background",
        }
        known_payload = {k: data.pop(k, None) for k in list(known_keys)}
        member_id = str(known_payload.get("id") or data.pop("id", None) or data.get("name") or "PC")
        name = str(data.pop("name", None) or known_payload.get("name") or member_id)
        extra = {k: v for k, v in data.items() if v is not None}
        extra.update({k: v for k, v in known_payload.items() if v is not None})
        return PartyMemberRef(
            id=member_id,
            name=name,
            class_=class_name,
            level=level_val,
            str_mod=str_mod,
            dex_mod=dex_mod,
            con_mod=con_mod,
            int_mod=int_mod,
            wis_mod=wis_mod,
            cha_mod=cha_mod,
            ac=ac,
            max_hp=max_hp_val,
            pb=pb,
            speed=speed,
            xp=xp_val,
            reach=reach_val,
            ranged=bool_values.get("ranged"),
            prof_athletics=bool_values.get("prof_athletics"),
            prof_acrobatics=bool_values.get("prof_acrobatics"),
            weapon_primary=extra.pop("weapon_primary", None),
            weapon_offhand=extra.pop("weapon_offhand", None),
            armor=extra.pop("armor", None),
            shield=bool_values.get("shield"),
            stealth_disadv=bool_values.get("stealth_disadv"),
            prof_skills=list_values.get("prof_skills"),
            prof_saves=list_values.get("prof_saves"),
            race=extra.pop("race", None),
            background=extra.pop("background", None),
            languages=list_values.get("languages"),
            tool_profs=list_values.get("tool_profs"),
            features=features_value,
            light_emitter=bool_values.get("light_emitter"),
            extra=extra,
        )

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "str_mod": self.str_mod,
            "dex_mod": self.dex_mod,
            "con_mod": self.con_mod,
            "int_mod": self.int_mod,
            "wis_mod": self.wis_mod,
            "cha_mod": self.cha_mod,
            "ac": self.ac,
            "max_hp": self.max_hp,
            "pb": self.pb,
            "speed": self.speed,
        }
        if self.class_ is not None:
            data["class"] = self.class_
        if self.level is not None:
            data["level"] = self.level
        if self.xp is not None:
            data["xp"] = self.xp
        if self.reach is not None:
            data["reach"] = self.reach
        optional_bools = {
            "ranged": self.ranged,
            "prof_athletics": self.prof_athletics,
            "prof_acrobatics": self.prof_acrobatics,
            "shield": self.shield,
            "stealth_disadv": self.stealth_disadv,
            "light_emitter": self.light_emitter,
        }
        for key, value in optional_bools.items():
            if value is not None:
                data[key] = bool(value)
        optional_lists = {
            "prof_skills": self.prof_skills,
            "prof_saves": self.prof_saves,
            "languages": self.languages,
            "tool_profs": self.tool_profs,
        }
        for key, value in optional_lists.items():
            if value:
                data[key] = list(value)
        if self.weapon_primary is not None:
            data["weapon_primary"] = self.weapon_primary
        if self.weapon_offhand is not None:
            data["weapon_offhand"] = self.weapon_offhand
        if self.armor is not None:
            data["armor"] = self.armor
        if self.features:
            data["features"] = dict(self.features)
        if self.race is not None:
            data["race"] = self.race
        if self.background is not None:
            data["background"] = self.background
        if self.extra:
            for key, value in self.extra.items():
                if key not in data and value is not None:
                    data[key] = value
        return data


@dataclass
class CampaignState:
    seed: int = 0
    day: int = 1
    time_of_day: str = "morning"
    location: str = "Wilderness"
    region: Optional[str] = None
    place: Optional[str] = None
    gold: int = 0
    inventory: Dict[str, Any] = field(default_factory=dict)
    party: List[PartyMemberRef] = field(default_factory=list)
    current_hp: Dict[str, int] = field(default_factory=dict)
    style: Optional[str] = None
    flags: Dict[str, Any] = field(default_factory=dict)
    journal: List[Any] = field(default_factory=list)
    quest_log: List[Dict[str, Any]] = field(default_factory=list)
    last_long_rest_day: int = 0
    encounter_chance: int = 30
    encounter_clock: int = 0
    encounter_clock_step: int = 10
    short_rest_hours: int = 4
    long_rest_to_morning: bool = True
    light_level: str = "normal"
    extras: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "CampaignState":
        data = dict(d or {})
        state_info = data.get("state") if isinstance(data.get("state"), dict) else {}
        clock_info = data.get("clock") if isinstance(data.get("clock"), dict) else {}
        location_value = data.get("location")
        location_info: Dict[str, Any] = {}
        if isinstance(location_value, dict):
            location_info = location_value
            location_text = location_value.get("name") or location_value.get("place")
        else:
            location_text = location_value
        if not location_info and isinstance(data.get("location_info"), dict):
            location_info = data["location_info"]
        region = data.get("region") or location_info.get("region")
        place = data.get("place") or location_info.get("place")
        if not location_text:
            location_text = place or location_info.get("name") or "Wilderness"
        seed_sources = [
            data.get("seed"),
            state_info.get("seed") if isinstance(state_info, dict) else None,
        ]
        seed = 0
        for candidate in seed_sources:
            if candidate is not None:
                try:
                    seed = int(candidate)
                    break
                except (TypeError, ValueError):
                    continue
        day_raw = data.get("day", clock_info.get("day", 1))
        try:
            day = int(day_raw)
        except (TypeError, ValueError):
            day = 1
        time_of_day = data.get("time_of_day") or clock_info.get("time") or "morning"
        gold_source = data.get("gold")
        party_info = data.get("party_info") if isinstance(data.get("party_info"), dict) else {}
        if not party_info and isinstance(data.get("party"), dict):
            party_info = data["party"]
        if gold_source is None and isinstance(party_info, dict):
            gold_source = party_info.get("gold")
        try:
            gold = int(gold_source) if gold_source is not None else 0
        except (TypeError, ValueError):
            gold = 0
        inventory = data.get("inventory") or {}
        if isinstance(inventory, list):
            upgraded: Dict[str, Any] = {}
            for item in inventory:
                key = str(item)
                upgraded[key] = upgraded.get(key, 0) + 1
            inventory = upgraded
        members_source: List[Dict[str, Any]] = []
        if isinstance(party_info.get("members"), list):
            members_source = [
                m for m in party_info["members"] if isinstance(m, dict)
            ]
        elif isinstance(data.get("party"), list):
            members_source = [m for m in data["party"] if isinstance(m, dict)]
        members = [PartyMemberRef.from_dict(m) for m in members_source]
        if not members and isinstance(data.get("party"), list):
            members = [PartyMemberRef.from_dict(m) for m in data["party"] if isinstance(m, dict)]
        current_hp: Dict[str, int] = {}
        hp_sources = []
        if isinstance(state_info, dict) and isinstance(state_info.get("current_hp"), dict):
            hp_sources.append(state_info["current_hp"])
        if isinstance(data.get("current_hp"), dict):
            hp_sources.append(data["current_hp"])
        for hp_map in hp_sources:
            for key, value in hp_map.items():
                try:
                    current_hp[str(key)] = int(value)
                except (TypeError, ValueError):
                    continue
        if not current_hp:
            for entry in members_source:
                pid = entry.get("id") or entry.get("name")
                if not pid:
                    continue
                hp = entry.get("hp") or {}
                if isinstance(hp, dict) and "current" in hp:
                    try:
                        current_hp[str(pid)] = int(hp["current"])
                    except (TypeError, ValueError):
                        pass
        style = data.get("style") or state_info.get("style") or data.get("narrative_style")
        flags = data.get("flags") if isinstance(data.get("flags"), dict) else {}
        journal_source = data.get("journal")
        if journal_source is None:
            journal_source = state_info.get("journal") if isinstance(state_info, dict) else None
        if journal_source is None:
            journal: List[Any] = []
        elif isinstance(journal_source, list):
            journal = list(journal_source)
        else:
            journal = [journal_source]
        quest_log_source = state_info.get("quest_log") if isinstance(state_info, dict) else None
        if not quest_log_source:
            quest_log_source = data.get("quest_log")
        if isinstance(quest_log_source, list):
            quest_log = [q for q in quest_log_source if isinstance(q, dict)]
        else:
            quest_log = []
        def _coerce_int(value: Any, default: int) -> int:
            try:
                return int(value)
            except (TypeError, ValueError):
                return default
        last_long_rest_day = _coerce_int(
            state_info.get("last_long_rest_day", data.get("last_long_rest_day")), 0
        )
        encounter_info = state_info.get("encounter") if isinstance(state_info, dict) else {}
        if not isinstance(encounter_info, dict):
            encounter_info = {}
        rest_info = state_info.get("rest") if isinstance(state_info, dict) else {}
        if not isinstance(rest_info, dict):
            rest_info = {}
        encounter_chance = _coerce_int(
            encounter_info.get("chance", data.get("encounter_chance")), 30
        )
        encounter_clock = _coerce_int(
            encounter_info.get("clock", data.get("encounter_clock")), 0
        )
        encounter_clock_step = _coerce_int(
            encounter_info.get("step", data.get("encounter_clock_step")), 10
        )
        short_rest_hours = _coerce_int(
            rest_info.get("short_hours", data.get("short_rest_hours")), 4
        )
        long_rest_to_morning_raw = rest_info.get(
            "long_to_morning", data.get("long_rest_to_morning")
        )
        if long_rest_to_morning_raw is None:
            long_rest_to_morning = True
        elif isinstance(long_rest_to_morning_raw, str):
            long_rest_to_morning = long_rest_to_morning_raw.strip().lower() in {
                "1",
                "true",
                "yes",
                "on",
                "y",
            }
        else:
            long_rest_to_morning = bool(long_rest_to_morning_raw)
        light_level = (
            state_info.get("light")
            if isinstance(state_info, dict) and state_info.get("light")
            else data.get("light_level", "normal")
        )
        extras = {
            "meta": data.get("meta") if isinstance(data.get("meta"), dict) else None,
        }
        extras = {k: v for k, v in extras.items() if v is not None}
        state = CampaignState(
            seed=seed,
            day=day,
            time_of_day=str(time_of_day),
            location=str(location_text or "Wilderness"),
            region=region,
            place=place,
            gold=gold,
            inventory=dict(inventory),
            party=members,
            current_hp=current_hp,
            style=str(style) if style else None,
            flags=dict(flags),
            journal=journal,
            quest_log=quest_log,
            last_long_rest_day=last_long_rest_day,
            encounter_chance=encounter_chance,
            encounter_clock=encounter_clock,
            encounter_clock_step=encounter_clock_step,
            short_rest_hours=short_rest_hours,
            long_rest_to_morning=long_rest_to_morning,
            light_level=str(light_level or "normal"),
            extras=extras,
        )
        for member in state.party:
            state.current_hp.setdefault(member.id, member.max_hp)
        return state

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "seed": self.seed,
            "day": self.day,
            "time_of_day": self.time_of_day,
            "gold": self.gold,
            "inventory": dict(self.inventory or {}),
            "party": [member.to_dict() for member in self.party],
            "current_hp": dict(self.current_hp or {}),
            "style": self.style,
            "narrative_style": self.style,
            "flags": dict(self.flags or {}),
            "journal": list(self.journal or []),
            "quest_log": list(self.quest_log or []),
            "last_long_rest_day": self.last_long_rest_day,
            "encounter_chance": self.encounter_chance,
            "encounter_clock": self.encounter_clock,
            "encounter_clock_step": self.encounter_clock_step,
            "short_rest_hours": self.short_rest_hours,
            "long_rest_to_morning": self.long_rest_to_morning,
            "light_level": self.light_level,
            "clock": {"day": self.day, "time": self.time_of_day},
        }
        if self.region or self.place:
            data["location"] = {
                "region": self.region,
                "place": self.place or self.location,
            }
        else:
            data["location"] = self.location
        id_to_current = dict(self.current_hp or {})
        if self.party:
            party_info_members: List[Dict[str, Any]] = []
            for member in self.party:
                member_blob = member.to_dict()
                current = id_to_current.get(member.id)
                if current is not None and current != member.max_hp:
                    member_blob["hp"] = {"max": member.max_hp, "current": current}
                else:
                    member_blob.pop("hp", None)
                party_info_members.append(member_blob)
            data["party_info"] = {"gold": self.gold, "members": party_info_members}
        rest_block = {
            "short_hours": self.short_rest_hours,
            "long_to_morning": self.long_rest_to_morning,
        }
        encounter_block = {
            "chance": self.encounter_chance,
            "clock": self.encounter_clock,
            "step": self.encounter_clock_step,
        }
        state_block = {
            "seed": self.seed,
            "current_hp": dict(self.current_hp or {}),
            "last_long_rest_day": self.last_long_rest_day,
            "encounter": encounter_block,
            "rest": rest_block,
            "light": self.light_level,
            "quest_log": list(self.quest_log or []),
            "style": self.style,
        }
        data["state"] = state_block
        if self.extras:
            data.update(self.extras)
        return data


__all__ = ["Quest", "Campaign", "PartyMemberRef", "CampaignState"]

