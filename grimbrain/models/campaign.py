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
    location: str = "Unknown"
    gold: int = 0
    inventory: Dict[str, Any] = field(default_factory=dict)
    party: List[Dict[str, Any]] = field(default_factory=list)
    style: Optional[str] = None
    flags: Dict[str, Any] = field(default_factory=dict)
    journal: List[Any] = field(default_factory=list)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "CampaignState":
        """Create CampaignState from both legacy and flat dict shapes."""

        data = dict(d or {})
        state_info = data.get("state") if isinstance(data.get("state"), dict) else {}
        meta_info = data.get("meta") if isinstance(data.get("meta"), dict) else {}
        clock_info = data.get("clock") if isinstance(data.get("clock"), dict) else {}

        def _coerce_int(value: Any, default: int) -> int:
            try:
                return int(value)
            except (TypeError, ValueError):
                return default

        day = _coerce_int(data.get("day", clock_info.get("day", 1)), 1)
        time_of_day = data.get("time_of_day") or clock_info.get("time") or "morning"

        location_value = data.get("location")
        location_info: Dict[str, Any] = {}
        if isinstance(location_value, dict):
            location_info = location_value
            loc_flat = None
        else:
            loc_flat = location_value if isinstance(location_value, str) else None
        if not location_info and isinstance(data.get("location_info"), dict):
            location_info = data["location_info"]
        region = data.get("region") or location_info.get("region")
        place = data.get("place") or location_info.get("place") or location_info.get("name")
        location = loc_flat or place or region or "Unknown"

        party_info = data.get("party_info") if isinstance(data.get("party_info"), dict) else {}
        if not party_info and isinstance(data.get("party"), dict):
            party_info = data["party"]
        gold = data.get("gold", party_info.get("gold"))
        gold_value = _coerce_int(gold, 0) if gold is not None else 0

        inventory_raw = data.get("inventory")
        if isinstance(inventory_raw, dict):
            inventory: Dict[str, Any] = dict(inventory_raw)
        elif isinstance(inventory_raw, list):
            inventory = {}
            for item in inventory_raw:
                key = str(item)
                inventory[key] = inventory.get(key, 0) + 1
        else:
            inventory = {}

        current_hp_map: Dict[str, int] = {}
        if isinstance(state_info.get("current_hp"), dict):
            for key, value in state_info["current_hp"].items():
                current_hp_map[str(key)] = _coerce_int(value, 0)
        if isinstance(data.get("current_hp"), dict):
            for key, value in data["current_hp"].items():
                current_hp_map[str(key)] = _coerce_int(value, 0)

        party_entries: List[Dict[str, Any]] = []
        if isinstance(party_info.get("members"), list):
            party_entries = [m for m in party_info["members"] if isinstance(m, dict)]
        elif isinstance(data.get("party"), list):
            party_entries = [m for m in data["party"] if isinstance(m, dict)]

        party: List[Dict[str, Any]] = []
        for entry in party_entries:
            member = dict(entry)
            hp_blob = member.pop("hp", None)
            hp_max = member.pop("hp_max", member.pop("max_hp", None))
            hp_current = member.pop("hp_current", member.pop("current_hp", None))
            if isinstance(hp_blob, dict):
                hp_max = hp_blob.get("max", hp_max)
                hp_current = hp_blob.get("current", hp_current)
            member_id = member.get("id") or member.get("name")
            if member_id is not None and hp_current is None:
                mapped = current_hp_map.get(str(member_id))
                if mapped is not None:
                    hp_current = mapped
            if hp_max is not None:
                try:
                    hp_max = int(hp_max)
                except (TypeError, ValueError):
                    hp_max = None
            if hp_current is not None:
                try:
                    hp_current = int(hp_current)
                except (TypeError, ValueError):
                    hp_current = None
            if hp_max is not None:
                member["hp_max"] = hp_max
            if hp_current is not None:
                member["hp_current"] = hp_current
            if "class_" in member and "class" not in member:
                member["class"] = member["class_"]
            party.append(member)

        style = (
            data.get("style")
            or state_info.get("style")
            or data.get("narrative_style")
            or meta_info.get("style")
        )

        flags_raw = data.get("flags") or state_info.get("flags")
        flags = dict(flags_raw) if isinstance(flags_raw, dict) else {}

        journal_raw = data.get("journal") or state_info.get("journal")
        if journal_raw is None:
            journal: List[Any] = []
        elif isinstance(journal_raw, list):
            journal = list(journal_raw)
        else:
            journal = [journal_raw]

        seed_value = (
            data.get("seed")
            or state_info.get("seed")
            or meta_info.get("seed")
            or meta_info.get("random_seed")
            or 0
        )
        seed = _coerce_int(seed_value, 0)

        return CampaignState(
            seed=seed,
            day=day,
            time_of_day=str(time_of_day),
            location=str(location),
            gold=gold_value,
            inventory=inventory,
            party=party,
            style=str(style) if style is not None else None,
            flags=flags,
            journal=journal,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Return a flat dict representation, suitable for JSON."""

        data: Dict[str, Any] = {
            "seed": self.seed,
            "day": self.day,
            "time_of_day": self.time_of_day,
            "location": self.location,
            "gold": self.gold,
            "inventory": dict(self.inventory),
            "party": [dict(member) for member in self.party],
            "style": self.style,
            "flags": dict(self.flags),
            "journal": list(self.journal),
        }
        return data


__all__ = ["Quest", "Campaign", "PartyMemberRef", "CampaignState"]

