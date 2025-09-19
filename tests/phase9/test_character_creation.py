import os
import tempfile

from grimbrain.engine.characters import (
    ability_mod,
    _point_buy_cost,
    build_partymember,
    load_pc,
    save_pc,
)


def test_ability_mod():
    assert ability_mod(8) == -1
    assert ability_mod(10) == 0
    assert ability_mod(15) == 2


def test_point_buy_cost_ok():
    scores = {"STR": 15, "DEX": 14, "CON": 14, "INT": 10, "WIS": 10, "CHA": 8}
    assert _point_buy_cost(scores) == 27


def test_build_and_roundtrip():
    pm = build_partymember(
        "Aria",
        "Fighter",
        {"STR": 15, "DEX": 14, "CON": 14, "INT": 10, "WIS": 10, "CHA": 8},
        weapon="Longsword",
        ranged=False,
    )
    assert pm.name == "Aria"
    assert pm.pb == 2
    assert pm.ac == 12
    assert pm.max_hp == 12

    with tempfile.TemporaryDirectory() as tmp:
        out_path = os.path.join(tmp, "Aria.json")
        save_pc(pm, out_path)
        pm2 = load_pc(out_path)
        assert pm2.name == "Aria"
        assert pm2.max_hp == pm.max_hp
