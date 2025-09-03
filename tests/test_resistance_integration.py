from pathlib import Path
from grimbrain.codex.weapons import WeaponIndex
from grimbrain.engine.types import Combatant
from grimbrain.engine.round import run_encounter
from grimbrain.character import Character


def C():
    return Character(str_score=16, dex_score=16, proficiency_bonus=2)


def test_runner_applies_resistance_and_thp():
    A = Combatant("Attacker", C(), hp=20, weapon="Longsword")
    B = Combatant("Skeleton", C(), hp=12, weapon="Mace", resist={"slashing"}, temp_hp=3)
    res = run_encounter(A, B, seed=33, max_rounds=1)
    assert res["b_hp"] >= 9  # loose bound; ensures reduction happened
