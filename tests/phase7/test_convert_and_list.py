import os
import subprocess
import sys
from pathlib import Path


def _run(cmd, env):
    return subprocess.check_output(cmd, env=env, text=True)


def test_convert_and_list(tmp_path):
    env = os.environ | {
        "GB_ENGINE": "data",
        "GB_RULES_DIR": "rules",
        "GB_CHROMA_DIR": str(tmp_path / "chroma"),
    }
    subprocess.check_call([sys.executable, "tools/convert_data_to_rules.py"], env=env)
    gen_dir = Path("rules/generated")
    attacks = list(gen_dir.glob("attack.*.json"))
    spells = list(gen_dir.glob("spell.*.json"))
    assert attacks and spells
    assert (gen_dir / "item.potion.healing.json").exists()
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "grimbrain.rules.index",
            "--rules",
            env["GB_RULES_DIR"],
            "--out",
            env["GB_CHROMA_DIR"],
        ],
        env=env,
    )
    out = _run([sys.executable, "main.py", "rules", "list"], env)
    first_attack = attacks[0].stem
    first_spell = spells[0].stem
    assert first_attack in out
    assert first_spell in out
    assert "item.potion.healing" in out
