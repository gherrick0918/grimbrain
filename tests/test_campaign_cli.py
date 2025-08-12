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


def run_cli(camp_dir: Path, inp: str, extra: list[str] | None = None) -> subprocess.CompletedProcess:
    main_path = Path(__file__).resolve().parent.parent / "main.py"
    args = [sys.executable, str(main_path), "--campaign", str(camp_dir)]
    if extra:
        args.extend(extra)
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
    def _victory(pcs, enemy, seed=None, **kwargs):
        return {"result": "victory", "summary": "", "hp": {p.name: p.hp for p in pcs}}

    def _defeat(pcs, enemy, seed=None, **kwargs):
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


def test_campaign_dir_path(tmp_path):
    camp_dir = _setup_campaign(tmp_path)
    proc = run_cli(camp_dir, "2\n", extra=["--max-rounds", "0"])
    assert proc.returncode == 0
    assert "Start" in proc.stdout or "Demo" in proc.stdout


def test_campaign_autostart(tmp_path):
    camp_dir = _setup_campaign(tmp_path)
    proc = run_cli(camp_dir, "2\n")
    assert "Start" in proc.stdout


def test_encounter_requires_pcs(tmp_path):
    campaign = {
        "name": "Demo",
        "start": "fight",
        "scenes": {
            "fight": {
                "text": "Fight!",
                "encounter": "goblin",
                "on_victory": "win",
                "on_defeat": "lose",
            },
            "win": {"text": "win"},
            "lose": {"text": "lose"},
        },
    }
    (tmp_path / "campaign.yaml").write_text(yaml.safe_dump(campaign))
    proc = run_cli(tmp_path, "", extra=["--max-rounds", "0"])
    assert proc.returncode != 0
    assert "no pcs were loaded" in proc.stderr.lower()


def test_rest_scene_save_resume(tmp_path):
    pc = {"name": "Hero", "ac": 15, "hp": 5, "max_hp": 10, "attacks": []}
    (tmp_path / "pc.json").write_text(json.dumps(pc))
    campaign = {
        "name": "RestDemo",
        "party_files": ["pc.json"],
        "start": "rest",
        "scenes": {
            "rest": {"text": "resting", "rest": "short", "on_victory": "end", "on_defeat": "end"},
            "end": {"text": "end"},
        },
    }
    (tmp_path / "campaign.yaml").write_text(yaml.safe_dump(campaign))
    save_path = tmp_path / "state.json"
    run_campaign_cli(tmp_path / "campaign.yaml", save=str(save_path), seed=1)
    state = json.loads(save_path.read_text())
    assert state["hp"]["Hero"] > 5
    run_campaign_cli(tmp_path / "campaign.yaml", resume=str(save_path))
