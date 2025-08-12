import subprocess
import sys
from pathlib import Path
import json
import yaml


def _setup(tmp_path: Path) -> Path:
    pc = {
        "name": "Hero",
        "ac": 15,
        "hp": 20,
        "attacks": [{"name": "Sword", "to_hit": 5, "damage_dice": "1d8+3", "type": "melee"}],
    }
    (tmp_path / "pc.json").write_text(json.dumps(pc))
    campaign = {
        "name": "Demo",
        "party_files": ["pc.json"],
        "start": "start",
        "scenes": {
            "start": {
                "text": "Start",
                "encounter": "goblin",
                "on_victory": "end",
                "on_defeat": "end",
            },
            "end": {"text": "Done"},
        },
    }
    (tmp_path / "campaign.yaml").write_text(yaml.safe_dump(campaign))
    return tmp_path


def test_log_files(tmp_path, monkeypatch):
    camp_dir = _setup(tmp_path)
    save_path = camp_dir / "sess.json"

    def _victory(pcs, enemy, seed=None):
        return {"result": "victory", "summary": "", "hp": {p.name: p.hp for p in pcs}}

    monkeypatch.setattr("grimbrain.engine.campaign.run_encounter", _victory)
    main_path = Path(__file__).resolve().parent.parent / "main.py"
    args = [
        sys.executable,
        str(main_path),
        "--campaign",
        str(camp_dir),
        "--save",
        str(save_path),
    ]
    subprocess.run(args, text=True, input="", capture_output=True, timeout=20, cwd=str(camp_dir))

    jsonl = save_path.with_suffix(".jsonl")
    md = save_path.with_suffix(".md")
    data = [json.loads(l) for l in jsonl.read_text().splitlines() if l.strip()]
    assert any(ev["type"] == "narration" for ev in data)
    assert any(ev["type"] == "encounter" for ev in data)
    assert "Start" in md.read_text()
