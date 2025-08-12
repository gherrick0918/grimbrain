import json
import subprocess
import sys
from pathlib import Path

from grimbrain.campaign import load_party_file


def test_pc_wizard_preset(tmp_path):
    out = tmp_path / "party.json"
    main_path = Path(__file__).resolve().parent.parent / "main.py"
    args = [
        sys.executable,
        str(main_path),
        "--pc-wizard",
        "--preset",
        "fighter",
        "--out",
        str(out),
    ]
    proc = subprocess.run(args, text=True, capture_output=True, timeout=20, cwd=str(main_path.parent))
    assert proc.returncode == 0
    assert out.exists()
    pcs = load_party_file(out)
    assert len(pcs) >= 1
