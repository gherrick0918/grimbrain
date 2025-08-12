from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Sequence


def _actions_len(data: dict) -> int:
    actions = data.get("actions") or []
    total = 0
    for a in actions:
        if isinstance(a, dict):
            total += len(a.get("text", ""))
        else:
            total += len(str(a))
    return total


def load_packs(names: Sequence[str], root: str | Path | None = None) -> Dict[str, dict]:
    """Load JSON sidecars from pack directories.

    ``names`` may be a list of pack names (looked up under ``root/packs``)
    or filesystem paths to pack folders or a directory containing multiple
    pack folders. ``root`` defaults to the repository root (one level above
    this file). Returns a catalog mapping normalized monster names to their
    JSON data. When multiple files share the same (name, source) pair, the
    entry with longer total action text is kept.
    """

    root_path = Path(root) if root else Path(__file__).resolve().parent.parent
    catalog: Dict[tuple[str, str], dict] = {}

    def _load_dir(pack_dir: Path) -> None:
        for path in pack_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text())
            except Exception:
                continue
            name = data.get("name")
            source = data.get("source", "")
            if not name:
                continue
            key = (name.lower(), source)
            existing = catalog.get(key)
            if existing is None or _actions_len(data) > _actions_len(existing):
                catalog[key] = data

    for pack in names:
        pack_path = Path(pack)
        if pack_path.is_dir():
            # ``pack`` may be a directory of JSON files or a root containing
            # multiple pack directories. If it has subdirectories we treat
            # those as packs, otherwise the directory itself is a pack.
            json_files = list(pack_path.glob("*.json"))
            subdirs = [d for d in pack_path.iterdir() if d.is_dir()]
            dirs = [pack_path] if json_files and not subdirs else subdirs
            for d in dirs:
                _load_dir(d)
            continue

        pack_dir = root_path / "packs" / pack
        if not pack_dir.exists():
            pack_dir = root_path / pack
        if pack_dir.exists():
            _load_dir(pack_dir)

    by_name: Dict[str, dict] = {}
    for (_name, _src), data in catalog.items():
        by_name[data["name"].lower()] = data
    return by_name
