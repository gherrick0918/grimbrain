import subprocess
import sys


def run(cmd, env, cwd):
    return subprocess.run(cmd, env=env, cwd=cwd, capture_output=True, text=True, check=True)


def test_content_list_filters(env_setup):
    env, root, _ = env_setup
    res = run([sys.executable, "main.py", "content", "list", "--type", "monster"], env, root)
    assert "monster/goblin" in res.stdout

    res2 = run([sys.executable, "main.py", "content", "list", "--grep", "goblin"], env, root)
    lines = [l for l in res2.stdout.splitlines() if l.strip()]
    assert len(lines) == 1 and "goblin" in lines[0]
