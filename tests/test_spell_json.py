from query_router import run_query
from models import SpellSidecar
from validators import validate_spell
import jsonschema
import pytest


def test_fireball_sidecar(embedder):
    md, js, prov = run_query(type="spell", query="fireball", embed_model=embedder)
    assert isinstance(js, dict)
    assert js["name"].lower() == "fireball"
    assert js["level"] == 3
    assert "Evocation" in js["school"]
    assert "Instant" in js["duration"]
    assert isinstance(prov, list) and prov
    validate_spell(js)
    SpellSidecar(**js)


def test_spell_schema_error():
    bad = {
        "name": "Fireball",
        "level": "three",
        "school": "Evocation",
        "casting_time": "1 action",
        "range": "150 ft",
        "components": "V,S,M",
        "duration": "Instant",
        "classes": ["Wizard"],
        "text": "Boom",
        "provenance": [],
    }
    with pytest.raises(jsonschema.ValidationError):
        validate_spell(bad)
