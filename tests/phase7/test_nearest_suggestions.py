import subprocess
import subprocess
import sys


def run(cmd, env, cwd):
    return subprocess.run(cmd, env=env, cwd=cwd, capture_output=True, text=True)


def test_nearest_suggestions(env_setup):
    env, root, _ = env_setup

    res = run([sys.executable, "main.py", "content", "show", "rule/attak.shortsowrd"], env, root)
    assert res.returncode == 2
    assert res.stdout.splitlines()[0].startswith("Not found:")
    assert "Did you mean:" in res.stdout
    assert "rule/attack.shortsword" in res.stdout

    res2 = run([sys.executable, "main.py", "rules", "show", "attak.shortsowrd"], env, root)
    assert res2.returncode == 2
    assert res2.stdout.splitlines()[0].startswith("Not found:")
    assert "Did you mean:" in res2.stdout
    assert "rule/attack.shortsword" in res2.stdout
