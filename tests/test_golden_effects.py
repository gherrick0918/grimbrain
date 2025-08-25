import os
import sys
import subprocess
import pathlib
import difflib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
MAIN = ROOT / "main.py"
GOLDEN = ROOT / "tests" / "golden"


def test_burning_pretty_golden():
    env = os.environ.copy()
    env.setdefault("GB_ENGINE", "data")
    env.setdefault("GB_RULES_DIR", "rules")
    env.setdefault("GB_CHROMA_DIR", ".chroma")
    env.setdefault("GB_RESOLVER_WARM_COUNT", "0")
    idx = [
        sys.executable,
        "-m",
        "grimbrain.rules.index",
        "--rules",
        "rules",
        "--out",
        ".chroma",
        "--packs",
        "packs/test_effects",
    ]
    subprocess.run(idx, cwd=str(ROOT), check=True, env=env, capture_output=True, text=True)
    subprocess.run([sys.executable, "-m", "grimbrain.rules.cli", "rules", "reload", "--packs", "packs/test_effects"], cwd=str(ROOT), check=True, env=env, capture_output=True, text=True)
    cmd = [
        sys.executable,
        str(MAIN),
        "play",
        "--pc",
        "tests/fixtures/pc_basic.json",
        "--encounter",
        "goblin",
        "--seed",
        "7",
        "--script",
        "tests/scripts/burning.txt",
    ]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, env=env)
    assert cp.returncode == 0
    got = cp.stdout
    want = (GOLDEN / "burning_pretty.golden").read_text(encoding="utf-8")

    def _norm(s: str) -> str:
        """Strip volatile indexing and cache-warm lines from CLI output."""
        lines = []
        for line in s.splitlines():
            if line.startswith("Indexed"):
                continue
            if line.startswith("Warmed resolver cache"):
                continue
            lines.append(line)
        return "\n".join(lines)

    got_n = _norm(got)
    want_n = _norm(want)
    if got_n != want_n:
        diff = "\n".join(
            difflib.unified_diff(
                want_n.splitlines(), got_n.splitlines(),
                fromfile="burning_pretty.golden", tofile="got", lineterm="",
            )
        )
        raise AssertionError(f"Golden mismatch:\n{diff}")

