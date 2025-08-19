import subprocess
import sys


def run(cmd, env, cwd):
    return subprocess.run(cmd, env=env, cwd=cwd, capture_output=True, text=True)


def test_unknown_verb_shows_suggestions(env_setup):
    env, root, _ = env_setup
    res = run([sys.executable, "-m", "grimbrain.rules.cli", "stablize", "Goblin"], env, root)
    assert res.returncode == 1
    lines = res.stdout.strip().splitlines()
    assert lines[0] == 'Not found verb: "stablize"'
    assert "Did you mean:" in res.stdout
    for word in ["attack", "heal", "stabilize", "spare"]:
        assert word in res.stdout


def test_alias_resolves(env_setup):
    env, root, _ = env_setup
    res = run([sys.executable, "main.py", "content", "show", "stab"], env, root)
    assert res.returncode == 0
    assert '"id": "attack"' in res.stdout
