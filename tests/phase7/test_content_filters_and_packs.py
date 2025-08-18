import subprocess
import sys


def run(cmd, env, cwd):
    return subprocess.run(cmd, env=env, cwd=cwd, capture_output=True, text=True, check=True)


def test_content_filters_and_packs(env_setup):
    env, root, _ = env_setup

    res_mon = run([sys.executable, "main.py", "content", "list", "--type", "monster"], env, root)
    assert any(l.strip() for l in res_mon.stdout.splitlines())

    res_spell = run([sys.executable, "main.py", "content", "list", "--type", "spell"], env, root)
    assert any(l.strip() for l in res_spell.stdout.splitlines())

    res_rule = run(
        [sys.executable, "main.py", "content", "list", "--type", "rule", "--grep", "short"],
        env,
        root,
    )
    lines = [l.split()[0] for l in res_rule.stdout.splitlines() if l.strip()]
    assert lines and all("short" in line for line in lines)

    packs = run([sys.executable, "main.py", "rules", "packs"], env, root)
    entries = [l for l in packs.stdout.splitlines() if l.strip()]
    names = {e.split(":")[0] for e in entries}
    assert {"legacy-data", "generated"} <= names
    for e in entries:
        int(e.split(":")[1].strip())
