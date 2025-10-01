from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:  # pragma: no cover - optional dependency
    import yaml  # type: ignore
except Exception:  # pragma: no cover - PyYAML is optional
    yaml = None  # type: ignore

from grimbrain.models.campaign import CampaignState


def _prune_empty_lists(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, inner in value.items():
            cleaned = _prune_empty_lists(inner)
            if isinstance(cleaned, list) and len(cleaned) == 0:
                continue
            result[key] = cleaned
        return result
    if isinstance(value, list):
        cleaned_items = [_prune_empty_lists(item) for item in value]
        return [item for item in cleaned_items if not (isinstance(item, list) and len(item) == 0)]
    return value


def _load_payload(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        if yaml is None:
            raise RuntimeError("PyYAML is required to read YAML")
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError("Campaign file must contain an object at the top level")
    return dict(data)


def load_campaign(path: str | Path) -> CampaignState:
    """Load a campaign document from disk as a CampaignState."""

    p = Path(path)
    data = _load_payload(p)
    return CampaignState.from_dict(data)


def save_campaign(state: CampaignState, path: str | Path, fmt: str | None = None) -> Path:
    """Persist a CampaignState to disk in JSON (default) or YAML."""

    if not isinstance(state, CampaignState):
        raise TypeError("save_campaign expects a CampaignState instance")

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
    payload = state.to_dict()
    if chosen == "yaml":
        if yaml is None:
            raise RuntimeError("PyYAML is required to write YAML")
        cleaned = _prune_empty_lists(payload)
        p.write_text(yaml.safe_dump(cleaned, sort_keys=False), encoding="utf-8")
    else:
        p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return p


__all__ = ["load_campaign", "save_campaign", "yaml"]
