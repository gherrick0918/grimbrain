import pathlib
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_rules_doctor_runs():
    cp = subprocess.run([sys.executable, "main.py", "rules", "doctor"], cwd=str(ROOT))
    assert cp.returncode in (0, 1, 2)

