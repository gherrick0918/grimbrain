import json
import subprocess
import sys
from pathlib import Path

from grimbrain.engine.session import Session

def test_cli_resume_offline(tmp_path):
    session = Session(scene="play", seed=1, steps=[{"round": 1}])
    save_path = tmp_path / "save.json"
    session.save(save_path)

    main_path = Path(__file__).resolve().parent.parent / "main.py"
    proc = subprocess.run(
        [sys.executable, str(main_path), "--resume", str(save_path)],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
    )
    assert proc.returncode == 0
    assert "Resumed scene 'play' with 1 steps" in proc.stdout
