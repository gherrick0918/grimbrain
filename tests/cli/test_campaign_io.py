import json
from pathlib import Path

import pytest

from grimbrain.io.campaign_io import load_campaign, save_campaign, yaml


def test_load_json_normalizes_legacy(tmp_path):
    p = tmp_path / "legacy.json"
    payload = {
        "seed": 5,
        "clock": {"day": 3, "time": "evening"},
        "location": {"region": "Greenfields", "place": "Village Gate"},
        "party": {
            "gold": 12,
            "members": [
                {
                    "id": "PC1",
                    "name": "Scout",
                    "hp": {"max": 10, "current": 7},
                    "ac": 13,
                }
            ],
        },
        "inventory": ["torch", "torch", "rations"],
        "state": {"current_hp": {"PC1": 7}},
    }
    p.write_text(json.dumps(payload), encoding="utf-8")

    state = load_campaign(p)
    assert state["day"] == 3
    assert state["time_of_day"] == "evening"
    assert state["location"] == "Greenfields: Village Gate"
    assert state["gold"] == 12
    assert state["inventory"] == {"torch": 2, "rations": 1}
    assert state["party"][0]["current_hp"] == 7
    assert state["current_hp"]["PC1"] == 7


def test_save_and_reload_roundtrip(tmp_path):
    p = tmp_path / "campaign.json"
    data = {
        "seed": 9,
        "day": 2,
        "time_of_day": "afternoon",
        "location": "Keep",
        "gold": 5,
        "inventory": {"rations": 3},
        "party": [
            {
                "id": "PC1",
                "name": "Ranger",
                "max_hp": 14,
                "current_hp": 11,
                "dex_mod": 3,
            }
        ],
        "style": "classic",
        "flags": {"mode": "solo"},
        "journal": ["entry"],
    }
    save_campaign(data, p)

    reloaded = load_campaign(p)
    assert reloaded["seed"] == 9
    assert reloaded["day"] == 2
    assert reloaded["time_of_day"] == "afternoon"
    assert reloaded["party"][0]["current_hp"] == 11
    assert reloaded["current_hp"]["PC1"] == 11
    assert reloaded["flags"]["mode"] == "solo"
    assert reloaded["journal"] == ["entry"]


def test_yaml_optional(tmp_path):
    p = tmp_path / "campaign.yaml"
    if yaml is None:
        pytest.skip("PyYAML not installed")

    data = {
        "seed": 2,
        "day": 1,
        "time_of_day": "morning",
        "location": "Outpost",
        "party": [],
        "inventory": {},
    }
    save_campaign(data, p, fmt="yaml")

    state = load_campaign(p)
    assert state["location"] == "Outpost"
    assert state["day"] == 1
