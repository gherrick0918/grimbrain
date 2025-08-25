import subprocess
import sys


def test_cli_help() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "grimbrain",
            "--help",
        ],
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert "Grimbrain" in completed.stdout
