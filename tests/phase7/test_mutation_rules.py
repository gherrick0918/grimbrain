import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from grimbrain.rules.resolver import RuleResolver
from grimbrain.rules.evaluator import Evaluator


def run(cmd, env, cwd):
    return subprocess.run(cmd, env=env, cwd=cwd, capture_output=True, text=True, check=True)


def test_mutation_rules(tmp_path):
    rules_root = tmp_path / "rules" / "generated"
    rules_root.mkdir(parents=True)
    rule_path = rules_root / "attack.shortsword.json"
    base_rule = {
        "id": "attack.shortsword",
        "kind": "action",
        "cli_verb": "attack.shortsword",
        "targets": ["target"],
        "effects": [{"op": "damage", "target": "target", "amount": "1d6"}],
    }
    rule_path.write_text(json.dumps(base_rule))
    chroma_dir = tmp_path / ".chroma"
    env = os.environ.copy()
    env.update({
        "GB_ENGINE": "data",
        "GB_RULES_DIR": str(tmp_path / "rules"),
        "GB_CHROMA_DIR": str(chroma_dir),
    })
    root = Path(__file__).resolve().parents[2]

    run([sys.executable, "-m", "grimbrain.rules.index", "--rules", str(tmp_path / "rules"), "--out", str(chroma_dir)], env, root)

    resolver = RuleResolver(rules_dir=str(tmp_path / "rules"), chroma_dir=str(chroma_dir))
    eva = Evaluator()
    rule, _ = resolver.resolve("attack.shortsword")
    ctx = {"actor": {"name": "Hero", "hp": 10}, "target": {"name": "Goblin", "hp": 10}, "seed": 9}
    logs = eva.apply(rule, ctx)
    base_amount = int(re.search(r"(\d+) damage", logs[0]).group(1))

    mutated = dict(base_rule)
    mutated["effects"] = [{"op": "damage", "target": "target", "amount": "1d8"}]
    rule_path.write_text(json.dumps(mutated))

    res = run([sys.executable, "-m", "grimbrain.rules.index", "--rules", str(tmp_path / "rules"), "--out", str(chroma_dir)], env, root)
    assert "+0 / ~1 / -0" in res.stdout

    resolver.reload()
    rule2, _ = resolver.resolve("attack.shortsword")
    ctx2 = {"actor": {"name": "Hero", "hp": 10}, "target": {"name": "Goblin", "hp": 10}, "seed": 9}
    logs2 = eva.apply(rule2, ctx2)
    new_amount = int(re.search(r"(\d+) damage", logs2[0]).group(1))
    assert new_amount > 6
    assert new_amount >= base_amount
