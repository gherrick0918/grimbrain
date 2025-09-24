"""Lightweight SRD loader for core 5e building blocks."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional

SRD_DIR = Path(__file__).resolve().parents[2] / "data" / "srd"
CACHE_DIR = Path.home() / ".grimbrain" / "srd_cache"


@dataclass(frozen=True)
class Armor:
    name: str
    category: str
    base_ac: int
    dex_cap: Optional[int]
    stealth_disadv: bool


@dataclass(frozen=True)
class Shield:
    name: str
    ac_bonus: int


@dataclass(frozen=True)
class ClassBasics:
    prof_saves: tuple[str, ...]
    prof_skills: tuple[str, ...]
    start_armor: tuple[str, ...]


@dataclass(frozen=True)
class SRDData:
    armors: Dict[str, Armor]
    shields: Dict[str, Shield]
    skills: Dict[str, str]
    classes: Dict[str, ClassBasics]


_SRD_CACHE: SRDData | None = None


def _load_json(name: str) -> object:
    path = SRD_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Missing SRD file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_srd(*, force_reload: bool = False) -> SRDData:
    """Load curated SRD snippets from disk and return dataclasses."""

    global _SRD_CACHE
    if _SRD_CACHE is not None and not force_reload:
        return _SRD_CACHE

    armors_raw = _load_json("armor.json")
    shields_raw = _load_json("shields.json")
    skills_raw = _load_json("skills.json")
    classes_raw = _load_json("classes_basic.json")

    armors = {entry["name"]: Armor(**entry) for entry in armors_raw}
    shields = {entry["name"]: Shield(**entry) for entry in shields_raw}
    classes: Dict[str, ClassBasics] = {}
    for cname, payload in classes_raw.items():
        classes[cname] = ClassBasics(
            prof_saves=tuple(payload.get("prof_saves", [])),
            prof_skills=tuple(payload.get("prof_skills", [])),
            start_armor=tuple(payload.get("start_armor", [])),
        )

    _SRD_CACHE = SRDData(
        armors=armors,
        shields=shields,
        skills={k: v for k, v in skills_raw.items()},
        classes=classes,
    )
    return _SRD_CACHE


def _canonical_lookup(name: str, options: Iterable[str]) -> Optional[str]:
    target = name.strip().lower()
    for candidate in options:
        if candidate.lower() == target:
            return candidate
    return None


def find_armor(name: str, data: SRDData | None = None) -> Optional[Armor]:
    if not name:
        return None
    data = data or load_srd()
    canon = _canonical_lookup(name, data.armors.keys())
    return data.armors.get(canon) if canon else None


def find_shield(name: str, data: SRDData | None = None) -> Optional[Shield]:
    if not name:
        return None
    data = data or load_srd()
    canon = _canonical_lookup(name, data.shields.keys())
    return data.shields.get(canon) if canon else None


def skill_ability(skill: str, data: SRDData | None = None) -> Optional[str]:
    if not skill:
        return None
    data = data or load_srd()
    canon = _canonical_lookup(skill, data.skills.keys())
    if canon is None:
        return None
    return data.skills[canon]


def fetch_srd_item(kind: str, slug: str, *, allow_online: bool | None = None) -> dict:
    """Fetch SRD JSON from dnd5eapi with a local disk cache.

    Online access is opt-in: pass ``allow_online=True`` or set
    ``GRIMBRAIN_SRD_ONLINE=1``. Results are cached under
    ``~/.grimbrain/srd_cache``.
    """

    if allow_online is None:
        allow_online = os.environ.get("GRIMBRAIN_SRD_ONLINE", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
    if not allow_online:
        raise RuntimeError(
            "Online SRD fetch disabled. Set GRIMBRAIN_SRD_ONLINE=1 or pass allow_online=True."
        )

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_name = f"{kind}_{slug}.json"
    cache_path = CACHE_DIR / cache_name
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))

    import urllib.request

    url = f"https://www.dnd5eapi.co/api/{kind}/{slug}"
    with urllib.request.urlopen(url, timeout=10) as response:
        data = json.loads(response.read().decode("utf-8"))
    cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data
