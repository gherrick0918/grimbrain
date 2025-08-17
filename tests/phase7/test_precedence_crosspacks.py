import subprocess
import sys
import json


def run(cmd, env, cwd):
    return subprocess.run(cmd, env=env, cwd=cwd, capture_output=True, text=True, check=True)


def test_precedence_crosspacks(env_setup, tmp_path):
    env, root, _ = env_setup
    pack1 = tmp_path / "pack1"
    pack1.mkdir()
    (pack1 / "pack.json").write_text(json.dumps({"name": "P1", "version": "1"}))
    (pack1 / "monsters").mkdir()
    (pack1 / "monsters" / "goblin.json").write_text(json.dumps({"name": "Goblin", "hp": 5}))

    pack2 = tmp_path / "pack2"
    pack2.mkdir()
    (pack2 / "pack.json").write_text(json.dumps({"name": "P2", "version": "1"}))
    (pack2 / "monsters").mkdir()
    (pack2 / "monsters" / "goblin.json").write_text(json.dumps({"name": "Goblin", "hp": 15}))

    res = run(
        [
            sys.executable,
            "main.py",
            "content",
            "reload",
            "--packs",
            f"{pack1},{pack2}",
        ],
        env,
        root,
    )
    assert res.stdout.lower().count("conflict for monster/goblin") == 1

    show = run([sys.executable, "main.py", "content", "show", "monster/goblin"], env, root)
    payload = json.loads(show.stdout)
    assert payload.get("hp") == 15
