from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import json
import yaml
from pydantic import BaseModel, Field

from .models import PC
from .models_character import load_pc_sheet


class Quest(BaseModel):
    id: str
    title: str
    status: str = "active"
    notes: List[str] = Field(default_factory=list)


class Campaign(BaseModel):
    name: str
    party_files: List[str]
    locations: List[Dict[str, Any]] = Field(default_factory=list)
    factions: List[Dict[str, Any]] = Field(default_factory=list)
    quests: List[Quest] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)
    seed: int | None = None
    last_session: str | None = None

    _path: Path | None = None

    def save(self, path: str | Path | None = None) -> Path:
        p = Path(path) if path else self._path
        if p is None:
            raise ValueError("Campaign path unknown")
        data = self.model_dump(exclude={"_path"}) if hasattr(self, "model_dump") else self.dict(exclude={"_path"})
        p.write_text(yaml.safe_dump(data, sort_keys=False))
        self._path = p
        return p


def load_campaign(path: str | Path) -> Campaign:
    p = Path(path)
    data = yaml.safe_load(p.read_text())
    camp = Campaign(**data)
    camp._path = p
    return camp


def load_party_file(path: Path) -> List[PC]:
    text = path.read_text()
    try:
        data = json.loads(text)
    except Exception:
        data = yaml.safe_load(text)
    if isinstance(data, list):
        raw = _normalize_party(data)
        return [PC(**obj) for obj in raw]
    if isinstance(data, dict) and "party" in data:
        raw = _normalize_party(data["party"])
        return [PC(**obj) for obj in raw]
    if isinstance(data, dict) and "class" in data and "abilities" in data:
        sheet = load_pc_sheet(path)
        return [sheet.to_pc()]
    raw = _normalize_party(data if isinstance(data, list) else [data])
    return [PC(**obj) for obj in raw]


def _normalize_party(raw: list[dict]) -> list[dict]:
    def _normalize_pc(obj: dict) -> dict:
        attacks = obj.get("attacks", [])
        for atk in attacks:
            if "damage_dice" not in atk and "damage" in atk:
                atk["damage_dice"] = atk.pop("damage")
            if "to_hit" not in atk and "attack_bonus" in atk:
                atk["to_hit"] = atk["attack_bonus"]
        return obj

    return [_normalize_pc(o) for o in raw]
