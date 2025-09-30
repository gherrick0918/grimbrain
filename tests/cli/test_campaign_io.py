from pathlib import Path
import json

from grimbrain.scripts.campaign_play import load_campaign, save_campaign, yaml


def test_load_json_roundtrip(tmp_path):
    p = tmp_path / "c.json"
    obj = {"clock": {"day": 2, "time": "noon"}}
    p.write_text(json.dumps(obj), encoding="utf-8")
    loaded = load_campaign(p)
    assert loaded["clock"]["day"] == 2


def test_save_json_default(tmp_path):
    p = tmp_path / "c.json"
    save_campaign({"x": 1}, p)
    assert json.loads(p.read_text())["x"] == 1


def test_yaml_optional(tmp_path):
    p = tmp_path / "c.yaml"
    if yaml is None:
        return
    save_campaign({"y": 2}, p, fmt="yaml")
    loaded = load_campaign(p)
    assert loaded["y"] == 2
