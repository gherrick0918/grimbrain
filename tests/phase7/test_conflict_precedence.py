import json
import subprocess
import sys
from pathlib import Path


def run(cmd, env, cwd):
    return subprocess.run(cmd, env=env, cwd=cwd, capture_output=True, text=True, check=True)


def test_conflict_precedence(env_setup):
    env, root, _ = env_setup
    rules_dir = Path(env["GB_RULES_DIR"])
    custom_file = rules_dir / "custom" / "shortsword.json"
    custom_file.write_text(
        json.dumps(
            {
                "id": "attack.shortsword",
                "name": "Shortsword",
                "kind": "attack",
                "subkind": "melee",
                "damage_dice": "2d6",
            }
        )
    )

    res = run([sys.executable, "main.py", "content", "reload"], env, root)
    assert res.stdout.count("Conflict: rule/attack.shortsword") == 1

    show = run([sys.executable, "main.py", "content", "show", "rule/attack.shortsword"], env, root)
    payload = json.loads(show.stdout)
    assert payload.get("damage_dice") == "2d6"
