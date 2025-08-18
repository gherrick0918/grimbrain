import subprocess
import sys


def run(cmd, env, cwd):
    return subprocess.run(cmd, env=env, cwd=cwd, capture_output=True, text=True, check=True)


def test_content_and_rules_shims(env_setup):
    env, root, _ = env_setup

    # content list with explicit type
    res = run([sys.executable, "main.py", "content", "list", "--type", "rule"], env, root)
    lines = [l for l in res.stdout.splitlines() if l.strip()]
    assert lines
    doc = lines[0].split()[0]

    # content show
    res_show = run([sys.executable, "main.py", "content", "show", doc], env, root)
    assert res_show.stdout.lstrip().startswith("{")

    # rules list shim
    res_rules_list = run([sys.executable, "main.py", "rules", "list"], env, root)
    assert any(l.strip() for l in res_rules_list.stdout.splitlines())

    # rules show shim
    _, doc_id = doc.split("/", 1)
    res_rules_show = run([sys.executable, "main.py", "rules", "show", doc_id], env, root)
    assert res_rules_show.stdout.lstrip().startswith("{")
