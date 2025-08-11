import subprocess
import sys


def test_tui_help_runs():
    result = subprocess.run([sys.executable, '-m', 'tui.app', '--help'], capture_output=True)
    assert result.returncode == 0
    assert b'Grimbrain TUI preview' in result.stdout
