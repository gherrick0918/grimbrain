import re
import subprocess
import sys


def test_indexer_prints_counts(tmp_path):
    out_dir = tmp_path / "chroma"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "grimbrain.rules.index",
            "--rules",
            "rules",
            "--out",
            str(out_dir),
        ],
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0
    m = re.search(
        r"Indexed (\d+) rules \(generated=\d+, custom=\d+, idx=[0-9a-f]{7}\)\.",
        proc.stdout,
    )
    assert m and int(m.group(1)) > 0
