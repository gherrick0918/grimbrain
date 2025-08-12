import json
import yaml
from pathlib import Path

from main import run_campaign_cli
from grimbrain.content import select


def test_random_encounter_variety(tmp_path, monkeypatch):
    pack_dir = tmp_path / "packs"
    pack_dir.mkdir()
    (pack_dir / "goblin.json").write_text(json.dumps({"name": "Goblin", "cr": "1", "tags": ["goblinoid"]}))
    (pack_dir / "goblin boss.json").write_text(json.dumps({"name": "Goblin Boss", "cr": "2", "tags": ["goblinoid"]}))
    monkeypatch.setattr(select, "PACK_ROOT", pack_dir)

    pc = {"name": "Hero", "ac": 15, "hp": 10, "attacks": [{"name": "Sword", "to_hit": 5, "damage_dice": "1d6", "type": "melee"}]}
    (tmp_path / "pc.json").write_text(json.dumps(pc))
    campaign = {
        "name": "Variety",
        "party_files": ["pc.json"],
        "start": "a",
        "scenes": {
            "a": {
                "text": "A",
                "encounter": {
                    "random": {"tags": ["goblinoid"], "cr": "1-2", "exclude_seen": True}
                },
                "on_victory": "b",
                "on_defeat": "b",
            },
            "b": {
                "text": "B",
                "encounter": {
                    "random": {"tags": ["goblinoid"], "cr": "1-2", "exclude_seen": True}
                },
                "on_victory": "end",
                "on_defeat": "end",
            },
            "end": {"text": "End"},
        },
    }
    (tmp_path / "campaign.yaml").write_text(yaml.safe_dump(campaign))
    seen = []

    def _run(pcs, enemy, **kwargs):
        seen.append(enemy)
        return {"result": "victory", "summary": "", "hp": {p.name: p.hp for p in pcs}}

    monkeypatch.setattr("grimbrain.engine.campaign.run_encounter", _run)
    run_campaign_cli(tmp_path / "campaign.yaml", seed=1)
    assert len(seen) == 2 and seen[0].lower() != seen[1].lower()
