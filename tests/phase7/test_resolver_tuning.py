import subprocess
import sys


def run(cmd, env, cwd):
    return subprocess.run(cmd, env=env, cwd=cwd, capture_output=True, text=True)


def test_suggestions_include_scores(env_setup):
    env, root, _ = env_setup
    env = dict(env)
    env["GB_RESOLVER_K"] = "5"
    env["GB_RESOLVER_MIN_SCORE"] = "0.1"
    res = run([sys.executable, "-m", "grimbrain.rules.cli", "attak", "Goblin"], env, root)
    assert res.returncode == 1
    out = res.stdout
    assert "Did you mean:" in out
    assert "(0." in out


def test_threshold_blocks_weak_hits(env_setup):
    env, root, _ = env_setup
    env = dict(env)
    env["GB_RESOLVER_MIN_SCORE"] = "0.99"
    res = run([sys.executable, "main.py", "content", "show", "rule/atk.shortsowrd"], env, root)
    assert "Not found" in res.stdout
    assert "Did you mean:" not in res.stdout


def test_warm_start_prints(env_setup):
    env, root, _ = env_setup
    env = dict(env)
    env["GB_RESOLVER_WARM_COUNT"] = "50"
    res = run([sys.executable, "main.py", "rules", "reload"], env, root)
    assert "Warmed resolver cache" in res.stdout
