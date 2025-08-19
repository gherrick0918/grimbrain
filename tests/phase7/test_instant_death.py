import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from grimbrain.rules.evaluator import Evaluator


def test_instant_death_off(monkeypatch):
    monkeypatch.delenv("GB_RULES_INSTANT_DEATH", raising=False)
    eva = Evaluator()
    actor = {"name": "Hero", "hp": 10, "max_hp": 10}
    rule = {"effects": [{"op": "damage", "target": "target", "amount": "20"}]}
    logs = eva.apply(rule, {"target": actor})
    assert actor["hp"] == 0
    assert actor.get("dying")
    assert not actor.get("dead")
    assert any("drops to 0 HP and is dying" in entry for entry in logs)


def test_instant_death_on(monkeypatch):
    monkeypatch.setenv("GB_RULES_INSTANT_DEATH", "true")
    eva = Evaluator()
    actor = {"name": "Hero", "hp": 10, "max_hp": 10}
    rule = {"effects": [{"op": "damage", "target": "target", "amount": "20"}]}
    logs = eva.apply(rule, {"target": actor})
    assert actor.get("dead")
    assert not actor.get("dying")
    assert any("dies outright." in entry for entry in logs)
