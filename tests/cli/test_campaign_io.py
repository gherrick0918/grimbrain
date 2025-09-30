from pathlib import Path
import json

from grimbrain.models.campaign import CampaignState
from grimbrain.scripts.campaign_play import load_campaign, save_campaign, yaml


def test_load_json_roundtrip(tmp_path):
    p = tmp_path / "c.json"
    obj = {"clock": {"day": 2, "time": "noon"}}
    p.write_text(json.dumps(obj), encoding="utf-8")
    loaded = load_campaign(p)
    assert isinstance(loaded, CampaignState)
    assert loaded.day == 2
    assert loaded.time_of_day == "noon"


def test_save_json_default(tmp_path):
    p = tmp_path / "c.json"
    state = CampaignState(seed=99, day=4, time_of_day="evening", location="Keep")
    save_campaign(state, p)
    payload = json.loads(p.read_text())
    assert payload["day"] == 4
    assert payload["time_of_day"] == "evening"


def test_yaml_optional(tmp_path):
    p = tmp_path / "c.yaml"
    if yaml is None:
        return
    state = CampaignState(seed=5, gold=12, party=[])
    save_campaign(state, p, fmt="yaml")
    loaded = load_campaign(p)
    assert isinstance(loaded, CampaignState)
    assert loaded.gold == 12
