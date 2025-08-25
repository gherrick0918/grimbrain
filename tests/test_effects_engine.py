import os, sys, subprocess, pathlib, json

ROOT = pathlib.Path(__file__).resolve().parents[1]
MAIN = ROOT / "main.py"


def run_play(script, seed=7, json_mode=True, packs="packs/test_effects"):
    env = os.environ.copy()
    env.setdefault("GB_ENGINE", "data")
    env.setdefault("GB_RULES_DIR", "rules")
    env.setdefault("GB_CHROMA_DIR", ".chroma")
    env.setdefault("GB_RESOLVER_WARM_COUNT", "0")
    if packs:
        idx = [
            sys.executable,
            "-m",
            "grimbrain.rules.index",
            "--rules",
            "rules",
            "--out",
            ".chroma",
            "--packs",
            packs,
        ]
        subprocess.run(idx, cwd=str(ROOT), check=True, capture_output=True, text=True, env=env)
        subprocess.run([sys.executable, "-m", "grimbrain.rules.cli", "rules", "reload", "--packs", packs], cwd=str(ROOT), check=True, capture_output=True, text=True, env=env)
    cmd = [
        sys.executable,
        str(MAIN),
        "play",
        "--pc",
        "tests/fixtures/pc_basic.json",
        "--encounter",
        "goblin",
        "--seed",
        str(seed),
        "--script",
        f"tests/scripts/{script}",
    ]
    if json_mode:
        cmd.append("--json")
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, env=env)
    return cp.returncode, cp.stdout, cp.stderr


def test_ignite_ticks_and_expires_json():
    code, out, err = run_play("burning.txt")
    assert code == 0
    lines = [json.loads(l) for l in out.splitlines() if l.strip()]
    kinds = [l.get("kind") for l in lines]
    assert "effect_started" in kinds
    assert kinds.count("effect_tick") >= 2
    assert "effect_expired" in kinds

