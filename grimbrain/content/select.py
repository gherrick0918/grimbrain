from __future__ import annotations

import json
import random
from pathlib import Path
from typing import List, Set

# Root directory containing monster packs. Tests may monkeypatch this.
PACK_ROOT = Path(__file__).resolve().parents[2] / "packs"


def _parse_cr(value: str | float | int | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        try:
            num, den = value.split("/")
            return float(int(num) / int(den))
        except Exception:
            return None


def _build_index(root: Path) -> List[dict]:
    entries: List[dict] = []
    if not root.exists():
        return entries
    for path in root.rglob("*.json"):
        try:
            data = json.loads(path.read_text())
        except Exception:
            continue
        name = data.get("name")
        if not name:
            continue
        cr = _parse_cr(data.get("cr"))
        tags = [t.lower() for t in data.get("tags", [])]
        entries.append({"name": name, "cr": cr, "tags": set(tags)})
    return entries


def select_monster(
    tags: list[str] | None = None,
    cr: str | None = None,
    exclude: Set[str] | None = None,
    seed: int | None = None,
) -> str:
    """Pick a monster from local packs deterministically by seed."""

    exclude_l = {e.lower() for e in (exclude or set())}
    index = _build_index(PACK_ROOT)

    candidates = []
    for entry in index:
        if entry["name"].lower() in exclude_l:
            continue
        if tags and not set(t.lower() for t in tags).issubset(entry["tags"]):
            continue
        if cr:
            if "-" in cr:
                lo, hi = cr.split("-", 1)
                try:
                    lo_f = float(lo)
                    hi_f = float(hi)
                    c = entry["cr"]
                    if c is None or not (lo_f <= c <= hi_f):
                        continue
                except ValueError:
                    pass
            else:
                try:
                    target = float(cr)
                    if entry["cr"] != target:
                        continue
                except ValueError:
                    pass
        candidates.append(entry["name"])

    if not candidates:
        raise ValueError("No monsters match criteria")
    rng = random.Random(seed)
    candidates.sort()
    return rng.choice(candidates)
