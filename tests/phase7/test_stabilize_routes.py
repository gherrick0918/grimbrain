import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from grimbrain.rules.evaluator import Evaluator


ROOT = Path(__file__).resolve().parents[2]


def load_rule(filename: str) -> dict:
    return json.loads((ROOT / "rules" / "custom" / filename).read_text())


def test_medicine_success_stabilizes():
    rule = load_rule("medicine.check.json")
    eva = Evaluator()
    actor = {"name": "Hero", "hp": 1, "skills": {"medicine"}}
    target = {"name": "Goblin", "hp": 0, "dying": True}
    ctx = {"actor": actor, "target": target, "mods": {"WIS": 5}, "prof": 2, "seed": 9}
    logs = eva.apply(rule, ctx)
    assert target.get("stable")
    assert any("stabilizes" in l for l in logs)


def test_medicine_fail_keeps_dying():
    rule = load_rule("medicine.check.json")
    eva = Evaluator()
    actor = {"name": "Hero", "hp": 1, "skills": set()}
    target = {"name": "Goblin", "hp": 0, "dying": True}
    ctx = {"actor": actor, "target": target, "mods": {"WIS": 0}, "prof": 2, "seed": 2}
    logs = eva.apply(rule, ctx)
    assert not target.get("stable")
    assert any("fails to stabilize" in l for l in logs)


def test_spare_dying_stabilizes_without_heal():
    rule = load_rule("spell.spare.dying.json")
    eva = Evaluator()
    actor = {"name": "Cleric", "hp": 5}
    target = {"name": "Goblin", "hp": 0, "dying": True, "death_failures": 1}
    ctx = {"actor": actor, "target": target}
    logs = eva.apply(rule, ctx)
    assert target.get("stable")
    assert target.get("death_failures") == 0
    assert any("is stable at 0 HP" in l for l in logs)
