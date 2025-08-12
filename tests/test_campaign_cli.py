import subprocess
import sys
from pathlib import Path

import yaml
import json

from grimbrain.campaign import load_campaign


def _setup_campaign(tmp_path: Path) -> Path:
    fighter = {
        "name": "Roth",
        "ac": 15,
        "hp": 20,
        "attacks": [{"name": "Sword", "to_hit": 5, "damage_dice": "1d8+3", "type": "melee"}],
    }
    wizard = {
        "name": "Brynn",
        "class": "Wizard",
        "level": 3,
        "abilities": {"str": 8, "dex": 14, "con": 12, "int": 16, "wis": 12, "cha": 10},
        "ac": 14,
        "hp": 16,
        "attacks": [
            {"name": "Quarterstaff", "proficient": True, "ability": "str", "damage_dice": "1d6+2", "type": "melee"}
        ],
    }
    (tmp_path / "pc_fighter.json").write_text(json.dumps(fighter))
    (tmp_path / "pc_wizard.json").write_text(json.dumps(wizard))
    campaign = {
        "name": "Greenvale Troubles",
        "party_files": ["pc_fighter.json", "pc_wizard.json"],
        "quests": [{"id": "q1", "title": "Bandits on the road", "status": "active"}],
        "notes": [],
        "seed": 42,
    }
    path = tmp_path / "campaign.yaml"
    path.write_text(yaml.safe_dump(campaign))
    return path


def run_play(cmds: str, campaign_file: Path) -> subprocess.CompletedProcess:
    main_path = Path(__file__).resolve().parent.parent / "main.py"
    args = [
        sys.executable,
        str(main_path),
        "--play",
        "--campaign",
        str(campaign_file),
        "--encounter",
        "goblin",
        "--max-rounds",
        "1",
        "--seed",
        "1",
    ]
    return subprocess.run(
        args,
        input=cmds,
        text=True,
        capture_output=True,
        timeout=20,
        cwd=str(campaign_file.parent),
    )


def test_campaign_commands_and_logging(tmp_path):
    camp_path = _setup_campaign(tmp_path)
    script = (
        "note \"Scary woods\"\n" "quest add \"Find relic\"\n" "quest done q1\n" "save\n" "end\n"
    )
    res = run_play(script, camp_path)
    assert res.returncode == 0
    camp = load_campaign(camp_path)
    assert any(q.id == "q2" and q.title == "Find relic" for q in camp.quests)
    q1 = next(q for q in camp.quests if q.id == "q1")
    assert q1.status == "done"
    assert "Scary woods" in camp.notes
    sess_dir = tmp_path / "campaigns" / "Greenvale Troubles" / "sessions"
    assert list(sess_dir.glob("*.json"))
    assert camp.last_session and Path(camp.last_session).exists()
