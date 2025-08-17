import subprocess
import sys
import json
import re


def run(cmd, env, cwd):
    return subprocess.run(cmd, env=env, cwd=cwd, capture_output=True, text=True, check=True)


def test_manifest_incremental_all_types(env_setup):
    env, root, data_dir = env_setup
    first = run([sys.executable, "main.py", "content", "reload"], env, root)
    idx1 = re.search(r"idx=([0-9a-f]{7})", first.stdout).group(1)

    mfile = data_dir / "monsters.json"
    monsters = json.loads(mfile.read_text())
    monsters[0]["hp"] = 8
    mfile.write_text(json.dumps(monsters))

    second = run([sys.executable, "main.py", "content", "reload"], env, root)
    upd = re.search(r"~(\d+)", second.stdout).group(1)
    idx2 = re.search(r"idx=([0-9a-f]{7})", second.stdout).group(1)
    assert upd == "1"
    assert idx1 != idx2
