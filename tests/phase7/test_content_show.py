import subprocess
import sys
import json


def run(cmd, env, cwd):
    return subprocess.run(cmd, env=env, cwd=cwd, capture_output=True, text=True, check=True)


def test_content_show(env_setup):
    env, root, _ = env_setup
    r = run([sys.executable, "main.py", "content", "show", "rule/attack.shortsword"], env, root)
    assert "Shortsword" in r.stdout

    r2 = run([sys.executable, "main.py", "content", "show", "monster/goblin"], env, root)
    data = json.loads(r2.stdout)
    assert data.get("hp") == 7
