from query_router import run_query, LAST_MONSTER_JSON
from models import MonsterSidecar
from validators import validate_monster
import jsonschema
import pytest

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
    validate_monster(data)
    MonsterSidecar(**data)


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
    validate_monster(data)
    MonsterSidecar(**data)


def test_run_query_returns_tuple(embedder):
    md, js, prov = run_query(type="monster", query="goblin", embed_model=embedder)
    assert isinstance(md, str)
    assert isinstance(js, dict)
    assert isinstance(prov, list) and prov


def test_schema_rejects_bad_type():
    bad = {
        "name": "Bad",
        "source": "MM",
        "ac": "10",
        "hp": "5",
        "speed": "30 ft.",
        "str": "eight",
        "dex": 10,
        "con": 10,
        "int": 10,
        "wis": 10,
        "cha": 10,
        "traits": [],
        "actions": [],
        "reactions": [],
        "provenance": [],
    }
    with pytest.raises(jsonschema.ValidationError):
        validate_monster(bad)

