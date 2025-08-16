import json
import os
from pathlib import Path

from grimbrain.rules.resolver import RuleResolver
from grimbrain.rules.evaluator import Evaluator
from grimbrain.rules import index


def _build(chroma):
    index.build_index("rules", chroma)


def _eval_attack(chroma):
    res = RuleResolver(rules_dir="rules", chroma_dir=chroma)
    rule, _ = res.resolve("attack")
    ctx = {
        "actor": {"name": "hero", "hp": 10, "tags": set(), "advantage": False},
        "target": {"name": "gob", "hp": 5, "tags": set(), "advantage": False},
        "mods": {},
        "prof": 0,
    }
    Evaluator().apply(rule, ctx)
    return ctx["target"]["hp"]


def test_mutation_changes_behavior(tmp_path):
    chroma = tmp_path / "chroma"
    _build(chroma)
    before = _eval_attack(chroma)
    path = Path("rules/attack.json")
    orig = path.read_text()
    try:
        data = json.loads(orig)
        data["effects"][0]["amount"] = "1d1+1"
        path.write_text(json.dumps(data))
        _build(chroma)
        after = _eval_attack(chroma)
    finally:
        path.write_text(orig)
        _build(chroma)
    assert before != after
