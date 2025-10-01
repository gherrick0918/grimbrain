from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict

try:  # pragma: no cover - optional dependency
    import yaml  # type: ignore
except Exception:  # pragma: no cover - PyYAML is optional
    yaml = None  # type: ignore


def _read_payload(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        if yaml is None:
            raise RuntimeError("PyYAML is required for YAML support")
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError("Campaign file must contain an object at the top level")
    return dict(data)


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_inventory(raw: Any) -> Dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        result: Dict[str, Any] = {}
        for key, value in raw.items():
            name = str(key)
            try:
                result[name] = int(value)
            except (TypeError, ValueError):
                result[name] = value
        return result
    if isinstance(raw, list):
        result: Dict[str, int] = {}
        for entry in raw:
            name = str(entry)
            result[name] = result.get(name, 0) + 1
        return result
    return {}


def _normalize_member(raw: Any, idx: int, hp_overrides: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(raw, dict):
        payload = dict(raw)
    else:
        payload = {"name": str(raw)}
    hp_info = payload.pop("hp", {}) or {}
    member_id = str(payload.get("id") or payload.get("name") or f"PC{idx}")
    name = str(payload.get("name") or member_id)
    hp_max_raw = payload.pop("hp_max", payload.pop("max_hp", hp_info.get("max")))
    hp_max = _coerce_int(hp_max_raw, default=12)
    hp_current_raw = payload.pop(
        "hp_current",
        payload.pop("current_hp", hp_info.get("current", hp_overrides.get(member_id))),
    )
    hp_current = _coerce_int(hp_current_raw, default=hp_max)
    member: Dict[str, Any] = {
        "id": member_id,
        "name": name,
        "hp_max": hp_max,
        "hp_current": max(0, min(hp_max, hp_current)),
    }
    for key in list(payload.keys()):
        value = payload[key]
        member[key] = value
    return member


def _location_string(data: Dict[str, Any]) -> str:
    location_value = data.get("location")
    if isinstance(location_value, dict):
        region = location_value.get("region")
        place = location_value.get("place") or location_value.get("location")
        name = location_value.get("name")
        if region and place:
            return f"{region}: {place}"
        return str(place or region or name or "Wilderness")
    if location_value:
        return str(location_value)
    loc_info = data.get("location_info")
    if isinstance(loc_info, dict):
        return str(
            loc_info.get("name")
            or loc_info.get("place")
            or loc_info.get("region")
            or "Wilderness"
        )
    return "Wilderness"


def load_campaign(path: str | Path) -> Dict[str, Any]:
    """Load a campaign document and normalize it to a plain dictionary."""

    p = Path(path)
    payload = _read_payload(p)
    state: Dict[str, Any] = dict(payload)

    clock = payload.get("clock") if isinstance(payload.get("clock"), dict) else {}
    state["seed"] = _coerce_int(payload.get("seed"), default=0)
    state["day"] = _coerce_int(payload.get("day", clock.get("day", 1)), default=1)
    state["time_of_day"] = str(payload.get("time_of_day", clock.get("time", "morning")))
    state["location"] = _location_string(payload)

    party_block = payload.get("party")
    members_source = None
    gold_value = payload.get("gold")
    if isinstance(party_block, dict):
        members_source = party_block.get("members")
        if gold_value is None and "gold" in party_block:
            gold_value = party_block.get("gold")
    elif isinstance(party_block, list):
        members_source = party_block

    party_info_block = payload.get("party_info")
    if members_source is None and isinstance(party_info_block, dict):
        members_source = party_info_block.get("members")
        if gold_value is None and "gold" in party_info_block:
            gold_value = party_info_block.get("gold")

    if members_source is None:
        members_source = []

    state["gold"] = _coerce_int(gold_value, default=0)
    state["inventory"] = _normalize_inventory(payload.get("inventory"))

    current_hp_source: Dict[str, Any] = {}
    if isinstance(payload.get("state"), dict):
        state_block = payload["state"]
        if isinstance(state_block.get("current_hp"), dict):
            current_hp_source.update({str(k): v for k, v in state_block["current_hp"].items()})
    if isinstance(payload.get("current_hp"), dict):
        current_hp_source.update({str(k): v for k, v in payload["current_hp"].items()})

    members: list[Dict[str, Any]] = []
    current_hp: Dict[str, int] = {}
    for idx, entry in enumerate(members_source or [], start=1):
        member = _normalize_member(entry, idx, current_hp_source)
        members.append(member)
        current_hp[member["id"]] = member.get("hp_current", member.get("hp_max", 0))
    state["party"] = members
    hp_map: Dict[str, int] = {}
    for key, value in (current_hp_source or {}).items():
        hp_map[str(key)] = _coerce_int(value, default=0)
    for key, value in current_hp.items():
        hp_map[key] = _coerce_int(value, default=value)
    state["current_hp"] = hp_map

    style_value = payload.get("style") or payload.get("narrative_style") or "classic"
    state["style"] = str(style_value)

    flags_raw = payload.get("flags")
    state["flags"] = dict(flags_raw) if isinstance(flags_raw, dict) else {}

    journal_raw = payload.get("journal")
    if isinstance(journal_raw, list):
        state["journal"] = list(journal_raw)
    elif journal_raw is None:
        state["journal"] = []
    else:
        state["journal"] = [journal_raw]

    quest_log_raw = payload.get("quest_log")
    if isinstance(quest_log_raw, list):
        state["quest_log"] = list(quest_log_raw)
    else:
        state["quest_log"] = []

    encounter_info = {}
    if isinstance(payload.get("state"), dict) and isinstance(payload["state"].get("encounter"), dict):
        encounter_info = payload["state"]["encounter"]
    state["encounter_chance"] = _coerce_int(
        payload.get("encounter_chance", encounter_info.get("chance", 30)),
        default=30,
    )
    state["encounter_clock"] = _coerce_int(
        payload.get("encounter_clock", encounter_info.get("clock", 0)),
        default=0,
    )
    state["encounter_clock_step"] = _coerce_int(
        payload.get("encounter_clock_step", encounter_info.get("step", 10)),
        default=10,
    )

    rest_info = {}
    if isinstance(payload.get("state"), dict) and isinstance(payload["state"].get("rest"), dict):
        rest_info = payload["state"]["rest"]
    state["short_rest_hours"] = _coerce_int(
        payload.get("short_rest_hours", rest_info.get("short_hours", 4)),
        default=4,
    )
    state["long_rest_to_morning"] = bool(
        payload.get("long_rest_to_morning", rest_info.get("long_to_morning", True))
    )
    state["last_long_rest_day"] = _coerce_int(
        payload.get("last_long_rest_day", payload.get("state", {}).get("last_long_rest_day", 0)),
        default=0,
    )
    state["light_level"] = str(
        payload.get("light_level", payload.get("state", {}).get("light", "normal"))
    )
    state["narrative_style"] = str(style_value)

    if not state.get("current_hp"):
        state["current_hp"] = {m["id"]: m.get("hp_current", m.get("hp_max", 0)) for m in members}

    return state


def save_campaign(data: Dict[str, Any], path: str | Path, fmt: str | None = None) -> Path:
    """Save a normalized campaign dictionary to disk."""

    if not isinstance(data, dict):
        raise TypeError("save_campaign expects a dictionary")

    p = Path(path)
    chosen = (fmt or "").lower() or None
    if chosen not in {None, "json", "yaml", "yml"}:
        raise ValueError("fmt must be json or yaml")
    if chosen is None:
        suffix = p.suffix.lower()
        if suffix in {".yaml", ".yml"}:
            chosen = "yaml"
        else:
            chosen = "json"

    payload = dict(data)
    raw_party = payload.get("party")
    if isinstance(raw_party, list):
        party_list = []
        for member in raw_party:
            if isinstance(member, dict):
                party_list.append(dict(member))
            elif is_dataclass(member):
                party_list.append(asdict(member))
            else:
                party_list.append({"name": str(member)})
    else:
        party_list = []
    payload["party"] = party_list
    style_value = payload.get("style") or payload.get("narrative_style") or "classic"
    payload["style"] = str(style_value)
    payload["narrative_style"] = str(style_value)
    payload.setdefault("inventory", {})
    payload.setdefault("journal", [])
    payload.setdefault("flags", {})

    current_hp_map = payload.get("current_hp")
    if not isinstance(current_hp_map, dict):
        current_hp_map = {}
    for member in party_list:
        if isinstance(member, dict):
            mid = member.get("id")
            if not mid:
                continue
            hp_value = member.get("hp_current", member.get("hp", member.get("hp_max", 0)))
            current_hp_map.setdefault(str(mid), _coerce_int(hp_value, default=0))
    payload["current_hp"] = {str(k): _coerce_int(v, default=0) for k, v in current_hp_map.items()}

    if chosen in {"yaml", "yml"}:
        if yaml is None:
            raise RuntimeError("PyYAML is required for YAML support")
        text = yaml.safe_dump(payload, sort_keys=False)
        text = text.replace(":\n  []", ": []").replace(":\n  {}", ": {}")
        p.write_text(text, encoding="utf-8")
    else:
        p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return p


__all__ = ["load_campaign", "save_campaign", "yaml"]
