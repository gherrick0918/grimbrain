import subprocess
import sys
from pathlib import Path
import json
import yaml

from grimbrain.engine.campaign import load_campaign
from main import run_campaign_cli


def _setup_campaign(tmp_path: Path) -> Path:
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
                "choices": [
                    {"text": "Fight", "next": "fight"},
                    {"text": "Run", "next": "lose"},
                    {"text": "Bridge", "next": "bridge"},
                ],
            },
            "fight": {
                "text": "A goblin appears",
                "encounter": "goblin",
                "on_victory": "win",
                "on_defeat": "lose",
            },
            "bridge": {
                "text": "Bridge",
                "check": {
                    "ability": "dexterity",
                    "dc": 4,
                    "on_success": "win",
                    "on_failure": "lose",
                },
            },
            "win": {"text": "You win!"},
            "lose": {"text": "You lose!"},
        },
    }
    (tmp_path / "campaign.yaml").write_text(yaml.safe_dump(campaign))
    return tmp_path


def run_cli(camp_dir: Path, inp: str) -> subprocess.CompletedProcess:
    main_path = Path(__file__).resolve().parent.parent / "main.py"
    args = [sys.executable, str(main_path), "--campaign", str(camp_dir)]
    # Ensure the input ends with a newline and set the correct working directory
    return subprocess.run(
        args,
        input=inp if inp.endswith('\n') else inp + '\n',
        text=True,
        capture_output=True,
        timeout=20,
        cwd=str(camp_dir),
    )


def test_campaign_load_and_branch(tmp_path, monkeypatch):
    camp_dir = _setup_campaign(tmp_path)
    camp = load_campaign(camp_dir)
    assert "start" in camp.scenes

    # choice branch
    proc = run_cli(camp_dir, "2\n")
    assert "You lose!" in proc.stdout

    # encounter branches executed in-process so we can stub RNG
    def _victory(pcs, enemy, seed=None):
        return {"result": "victory", "summary": "", "hp": {p.name: p.hp for p in pcs}}

    def _defeat(pcs, enemy, seed=None):
        return {"result": "defeat", "summary": "", "hp": {p.name: p.hp for p in pcs}}

    monkeypatch.setattr("grimbrain.engine.campaign.run_encounter", _victory)
    run_campaign_cli(camp_dir, start="fight")

    monkeypatch.setattr("grimbrain.engine.campaign.run_encounter", _defeat)
    run_campaign_cli(camp_dir, start="fight")


def test_check_scene_branch(tmp_path, monkeypatch, capfd):
    camp_dir = _setup_campaign(tmp_path)

    def _success(mod, dc, advantage=False, seed=None):
        return {"roll": 10, "total": 10, "success": True}

    def _failure(mod, dc, advantage=False, seed=None):
        return {"roll": 1, "total": 1, "success": False}

    monkeypatch.setattr("grimbrain.engine.checks.roll_check", _success)
    run_campaign_cli(camp_dir, start="bridge")
    out = capfd.readouterr().out
    assert "You win!" in out

    monkeypatch.setattr("grimbrain.engine.checks.roll_check", _failure)
    run_campaign_cli(camp_dir, start="bridge")
    out = capfd.readouterr().out
    assert "You lose!" in out
