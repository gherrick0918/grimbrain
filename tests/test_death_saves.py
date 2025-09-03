from grimbrain.engine.types import Combatant, DeathState
from grimbrain.engine.death import roll_death_save, apply_damage_while_down, reset_death_state
from grimbrain.engine.round import run_encounter
from grimbrain.engine.scene import run_scene
from grimbrain.character import Character


def C():  # vanilla char
    return Character(str_score=14, dex_score=14, proficiency_bonus=2)


def test_roll_sequence_stabilizes_or_dies_deterministically_with_seed():
    ds = DeathState()
    import random
    rng = random.Random(7)
    seen = []
    for _ in range(5):
        seen.append(roll_death_save(ds, rng))
        if ds.stable or ds.dead:
            break
    assert ds.stable or ds.dead
    assert any("success" in s or "fail" in s for s in seen)


def test_damage_while_down_causes_failures_and_death():
    ds = DeathState()
    apply_damage_while_down(ds, melee_within_5ft=False)
    assert ds.failures == 1 and not ds.dead
    apply_damage_while_down(ds, melee_within_5ft=True)
    assert ds.failures == 3 and ds.dead


def test_round_runner_continues_until_death_or_stable():
    a = Combatant("A", C(), hp=1, weapon="Longsword")
    b = Combatant("B", C(), hp=1, weapon="Mace")
    res = run_encounter(a, b, seed=3, max_rounds=10)
    # With low HP, one side should die within a few rounds
    assert res["winner"] in {"A", "B"}


def test_scene_logs_death_save_and_finish():
    a = Combatant("A", C(), hp=1, weapon="Longsword")
    b = Combatant("B", C(), hp=1, weapon="Mace")
    res = run_scene(a, b, seed=5, max_rounds=6, start_distance_ft=5)
    log = "\n".join(res.log).lower()
    assert "death save" in log and ("dies." in log or "is stable" in log)

