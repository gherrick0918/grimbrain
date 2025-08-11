from engine.combat import run_encounter, parse_monster_spec
from tests.test_combat_round import make_goblin, make_goblin_boss, make_pc


def lookup(name: str):
    name = name.lower()
    if name == "goblin":
        return make_goblin()
    if name == "goblin boss":
        return make_goblin_boss()
    raise KeyError(name)


def test_encounter_deterministic_and_max_rounds():
    pcs = [make_pc()]
    monsters = [make_goblin()]
    res = run_encounter(pcs, monsters, seed=1)
    assert res["winner"] == "monsters" and res["rounds"] == 5
    assert res["state"]["party"][0]["hp"] == -1
    res_max = run_encounter(pcs, [make_goblin()], seed=1, max_rounds=1)
    assert res_max["rounds"] == 1 and res_max["winner"] == "none"


def test_parse_encounter_and_hp():
    mons = parse_monster_spec("goblin x3, goblin boss", lookup)
    assert [m.name for m in mons] == ["Goblin", "Goblin", "Goblin", "Goblin Boss"]
    pcs = [make_pc()]
    res1 = run_encounter(pcs, parse_monster_spec("goblin x3, goblin boss", lookup), seed=0, max_rounds=1)
    res2 = run_encounter(pcs, parse_monster_spec("goblin x3, goblin boss", lookup), seed=0, max_rounds=1)
    assert res1["state"] == res2["state"]


def test_summary_xp():
    pcs = [make_pc()]
    boss = make_goblin_boss()
    res = run_encounter(pcs, [boss], seed=2)
    assert res["summary"]["xp"] > 0
