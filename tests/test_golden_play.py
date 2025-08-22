import os
import sys
import subprocess
import pathlib
import difflib
import tempfile
import shutil


ROOT = pathlib.Path(__file__).resolve().parents[1]
MAIN = ROOT / "main.py"
FX = ROOT / "tests" / "fixtures"
SCRIPTS = ROOT / "tests" / "scripts"
GOLDEN = ROOT / "tests" / "golden"


def run_play(script_name, seed, json_mode=True, summary_only=False):
    pc = FX / "pc_basic.json"
    script = SCRIPTS / script_name
    cmd = [
        sys.executable,
        str(MAIN),
        "play",
        "--pc",
        str(pc),
        "--encounter",
        "goblin",
        "--seed",
        str(seed),
        "--script",
        str(script),
    ]
    if json_mode:
        cmd.append("--json")
    if summary_only:
        cmd.append("--summary-only")
    env = os.environ.copy()
    env["GB_ENGINE"] = "data"
    env["GB_RULES_DIR"] = "rules"
    chroma_dir = tempfile.mkdtemp(prefix="chroma_")
    env["GB_CHROMA_DIR"] = chroma_dir
    env["GB_RESOLVER_WARM_COUNT"] = "0"
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, env=env)
    shutil.rmtree(chroma_dir, ignore_errors=True)
    return cp.returncode, cp.stdout


def assert_matches_golden(name, got):
    golden_path = GOLDEN / f"{name}.golden"
    want = golden_path.read_text(encoding="utf-8")

    def _norm(s: str) -> str:
        import re

        s = re.sub(r"Warmed resolver cache.*\n", "", s)
        s = re.sub(r"Indexed.*\n", "", s)
        s = re.sub(r"\s*idx=[0-9a-f]+\)\.\n", "", s)
        s = re.sub(r"Did you mean:.*\n", "", s)
        return s

    got_n = _norm(got)
    want_n = _norm(want)
    if got_n != want_n:
        diff = "\n".join(
            difflib.unified_diff(
                want_n.splitlines(),
                got_n.splitlines(),
                fromfile=f"{name}.golden",
                tofile="got",
                lineterm="",
            )
        )
        raise AssertionError(f"Golden mismatch for {name}:\n{diff}")


def test_attack_summary_json():
    code, out = run_play("attack.txt", seed=7, json_mode=True, summary_only=True)
    assert code == 0
    assert_matches_golden("attack_summary_json", out)


def test_hide_full_pretty():
    code, out = run_play("hide.txt", seed=7, json_mode=False, summary_only=False)
    assert code == 0
    assert_matches_golden("hide_full_pretty", out)

