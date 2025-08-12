import json
from pathlib import Path

from grimbrain.content.packs import load_packs


def test_pack_dedup_prefers_longer_actions(tmp_path):
    p1 = tmp_path / "packs" / "a"
    p2 = tmp_path / "packs" / "b"
    p1.mkdir(parents=True)
    p2.mkdir(parents=True)
    base = {
        "name": "Beast",
        "source": "HB",
        "ac": "10",
        "hp": "1",
        "speed": "30 ft.",
        "str": 1,
        "dex": 1,
        "con": 1,
        "int": 1,
        "wis": 1,
        "cha": 1,
        "traits": [],
        "actions_struct": [],
        "reactions": [],
        "provenance": []
    }
    short = dict(base, actions=[{"name": "Hit", "text": "x"}])
    long = dict(base, actions=[{"name": "Hit", "text": "x"}, {"name": "Claw", "text": "y"}])
    (p1 / "beast.json").write_text(json.dumps(short))
    (p2 / "beast.json").write_text(json.dumps(long))

    cat = load_packs(["a", "b"], root=tmp_path)
    assert len(cat["beast"]["actions"]) == 2
