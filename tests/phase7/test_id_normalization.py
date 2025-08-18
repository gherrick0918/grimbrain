import subprocess
import sys


def run(cmd, env, cwd, check=True):
    return subprocess.run(cmd, env=env, cwd=cwd, capture_output=True, text=True, check=check)


def test_id_normalization(env_setup):
    env, root, _ = env_setup

    res = run([sys.executable, "main.py", "content", "list", "--type", "monster"], env, root)
    assert "monster/goblin" in res.stdout
    assert "monster/monster.goblin" not in res.stdout

    res2 = run([sys.executable, "main.py", "content", "show", "monster/goblin"], env, root)
    assert res2.stdout.lstrip().startswith("{")

    res3 = run([sys.executable, "main.py", "content", "show", "monster/monster.goblin"], env, root)
    assert res3.stdout.lstrip().startswith("{")
