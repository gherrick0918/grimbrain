from grimbrain.engine.combat import run_encounter
from tests.test_combat_round import make_goblin, make_pc


def test_combat_determinism_seed():
    pcs = [make_pc()]
    monsters = [make_goblin()]
    res1 = run_encounter(pcs, monsters, seed=5)
    res2 = run_encounter(pcs, [make_goblin()], seed=5)
    assert res1["state"] == res2["state"] and res1["log"] == res2["log"]
    res3 = run_encounter(pcs, [make_goblin()], seed=6)
    assert res1["state"] != res3["state"]
