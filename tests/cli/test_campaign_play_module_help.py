import subprocess
import sys

import pytest

from grimbrain.scripts import campaign_play as cp


def test_module_help_runs():
    if not hasattr(cp.app, "main"):
        pytest.skip("Typer stub does not expose CLI runner")
    result = subprocess.run(
        [sys.executable, "-m", "grimbrain.scripts.campaign_play", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    out = result.stdout or result.stderr
    assert "Usage" in out or "usage" in out
