import json
from pathlib import Path

import jsonschema

from query_router import run_query

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "spell.json"
with open(SCHEMA_PATH) as f:
    SPELL_SCHEMA = json.load(f)


def test_fireball_sidecar(embedder):
    md, js, prov = run_query(type="spell", query="fireball", embed_model=embedder)
    assert isinstance(js, dict)
    assert js["name"].lower() == "fireball"
    assert js["level"] == 3
    assert "Evocation" in js["school"]
    assert "Instant" in js["duration"]
    assert isinstance(prov, list)
    jsonschema.validate(js, SPELL_SCHEMA)
