from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import yaml
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from grimbrain.models.pc import PlayerCharacter
from grimbrain.models.campaign import Campaign


SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schema"


class PrettyError(Exception):
    pass


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


_def_schemas = {
    "pc": SCHEMA_DIR / "pc.schema.json",
    "campaign": SCHEMA_DIR / "campaign.schema.json",
}


def _validate_jsonschema(obj: Any, schema_path: Path) -> None:
    schema = _read_json(schema_path)
    v = Draft202012Validator(schema)
    errors = sorted(v.iter_errors(obj), key=lambda e: e.path)
    if errors:
        lines = []
        for e in errors[:5]:
            ptr = "/" + "/".join([str(p) for p in e.path])
            lines.append(f"- {ptr or '/'}: {e.message}")
        more = "" if len(errors) <= 5 else f" (+{len(errors)-5} more)"
        raise PrettyError("JSON Schema validation failed:\n" + "\n".join(lines) + more)


def _migrate_spells_legacy(data: dict) -> dict:
    if "spells" in data and "known_spells" not in data:
        if isinstance(data["spells"], list):
            data["known_spells"] = list(dict.fromkeys(data["spells"]))
        del data["spells"]
    return data


# Public API


def load_pc(path: Path) -> PlayerCharacter:
    data = _read_json(path)
    data = _migrate_spells_legacy(data)
    _validate_jsonschema(data, _def_schemas["pc"])
    try:
        return PlayerCharacter.model_validate(data)
    except ValidationError as e:
        raise PrettyError(e.errors(include_url=False))


def load_campaign(path: Path) -> Campaign:
    data = _read_yaml(path)
    _validate_jsonschema(data, _def_schemas["campaign"])
    try:
        return Campaign.model_validate(data)
    except ValidationError as e:
        raise PrettyError(e.errors(include_url=False))


__all__ = ["load_pc", "load_campaign", "PrettyError"]

