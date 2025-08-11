import json
from pathlib import Path

import jsonschema

from query_router import run_query, LAST_MONSTER_JSON

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "monster.json"
with open(SCHEMA_PATH) as f:
    MONSTER_SCHEMA = json.load(f)

def _names(items):
    return [i["name"] for i in items]

def test_goblin_sidecar(embedder):
    run_query(type="monster", query="goblin", embed_model=embedder)
    data = LAST_MONSTER_JSON
    assert data["name"].lower() == "goblin"
    assert data["ac"].startswith("15")
    assert data["hp"].startswith("7")
    assert data["speed"].startswith("30")
    assert data["str"] == 8
    assert data["dex"] == 14
    assert data["con"] == 10
    assert data["int"] == 10
    assert data["wis"] == 8
    assert data["cha"] == 8
    assert "Nimble Escape" in _names(data["traits"])
    assert "Scimitar" in _names(data["actions"])
    assert "Shortbow" in _names(data["actions"])
    assert data["reactions"] == []
    jsonschema.validate(data, MONSTER_SCHEMA)


def test_goblin_boss_sidecar(embedder):
    run_query(type="monster", query="goblin boss", embed_model=embedder)
    data = LAST_MONSTER_JSON
    assert data["name"].lower() == "goblin boss"
    assert data["ac"].startswith("17")
    assert data["hp"].startswith("21")
    assert data["str"] == 10
    assert data["dex"] == 14
    assert "Nimble Escape" in _names(data["traits"])
    assert "Multiattack" in _names(data["actions"])
    assert any(r["name"] == "Redirect Attack" for r in data["reactions"])
    jsonschema.validate(data, MONSTER_SCHEMA)


def test_run_query_returns_tuple(embedder):
    md, js, prov = run_query(type="monster", query="goblin", embed_model=embedder)
    assert isinstance(md, str)
    assert isinstance(js, dict)
    assert isinstance(prov, list)

