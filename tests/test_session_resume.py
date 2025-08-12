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
            "start": {"text": "Start", "choices": [{"text": "Next", "next": "middle"}]},
            "middle": {"text": "Middle", "choices": [{"text": "End", "next": "end"}]},
            "end": {"text": "The End"},
        },
    }
    (tmp_path / "campaign.yaml").write_text(yaml.safe_dump(campaign))
    return tmp_path


def run(path: Path, save: Path | None, resume: Path | None, inp: str) -> subprocess.CompletedProcess:
    main_path = Path(__file__).resolve().parent.parent / "main.py"
    args = [sys.executable, str(main_path), "--campaign", str(path)]
    if save:
        args += ["--save", str(save)]
    if resume:
        args += ["--resume", str(resume)]
    return subprocess.run(args, input=inp, text=True, capture_output=True, timeout=20, cwd=str(path))


def test_save_and_resume(tmp_path):
    camp_dir = _setup(tmp_path)
    save_path = camp_dir / "state.json"

    run(camp_dir, save_path, None, "1\n")
    state = json.loads(save_path.read_text())
    assert state["scene"] == "middle"

    res = run(camp_dir, save_path, save_path, "1\n")
    assert "The End" in res.stdout
