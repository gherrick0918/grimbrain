import json
from pathlib import Path

from grimbrain.content import select


def test_select_exclude(tmp_path, monkeypatch):
    pack_dir = tmp_path / "packs"
    pack_dir.mkdir()
    (pack_dir / "goblin.json").write_text(json.dumps({"name": "Goblin", "cr": "1", "tags": ["goblinoid"]}))
    (pack_dir / "goblin boss.json").write_text(
        json.dumps({"name": "Goblin Boss", "cr": "2", "tags": ["goblinoid"]})
    )
    monkeypatch.setattr(select, "PACK_ROOT", pack_dir)
    for _ in range(5):
        assert select.select_monster(tags=["goblinoid"], cr="1-2", exclude={"goblin boss"}, seed=1) == "Goblin"
