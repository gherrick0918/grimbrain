import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from grimbrain.rules.evaluator import Evaluator


def test_drop_to_zero_enters_dying():
    eva = Evaluator()
    actor = {"name": "Hero", "hp": 3}
    rule = {"effects": [{"op": "damage", "target": "target", "amount": "5"}]}
    logs = eva.apply(rule, {"target": actor})
    assert actor["hp"] == 0
    assert actor.get("dying")
    assert not actor.get("stable")
    assert any("drops to 0 HP and is dying" in l for l in logs)


def test_stable_then_damage_fails_one():
    eva = Evaluator()
    actor = {"name": "Hero", "hp": 0}
    stabilize = {
        "effects": [
            {"op": "set_stable", "target": "target"},
            {"op": "clear_death_saves", "target": "target"},
        ]
    }
    eva.apply(stabilize, {"target": actor})
    dmg_rule = {"effects": [{"op": "damage", "target": "target", "amount": "1"}]}
    logs = eva.apply(dmg_rule, {"target": actor})
    assert actor.get("death_failures") == 1
    assert actor.get("dying") and not actor.get("stable")
    assert any("fails a death save (1/3)" in l for l in logs)


def test_critical_at_zero_fails_two():
    eva = Evaluator()
    actor = {"name": "Hero", "hp": 0}
    stabilize = {
        "effects": [
            {"op": "set_stable", "target": "target"},
            {"op": "clear_death_saves", "target": "target"},
        ]
    }
    eva.apply(stabilize, {"target": actor})
    dmg_rule = {
        "effects": [
            {"op": "damage", "target": "target", "amount": "1", "tags": ["critical"]}
        ]
    }
    logs = eva.apply(dmg_rule, {"target": actor})
    assert actor.get("death_failures") == 2
    assert any("Critical hit!" in l for l in logs)


def test_heal_clears_death_saves():
    eva = Evaluator()
    actor = {"name": "Hero", "hp": 0, "death_failures": 1, "dying": True}
    heal_rule = {"effects": [{"op": "heal", "target": "target", "amount": "5"}]}
    logs = eva.apply(heal_rule, {"target": actor})
    assert actor["hp"] > 0
    assert actor.get("death_failures") == 0
    assert not actor.get("dying") and not actor.get("stable")
    assert any("no longer dying" in l for l in logs)


def test_three_failures_die():
    eva = Evaluator()
    actor = {"name": "Hero", "hp": 0, "dying": True}
    dmg_rule = {"effects": [{"op": "damage", "target": "target", "amount": "1"}]}
    for _ in range(2):
        eva.apply(dmg_rule, {"target": actor})
    logs = eva.apply(dmg_rule, {"target": actor})
    assert actor.get("dead")
    assert any("dies." in l for l in logs)
