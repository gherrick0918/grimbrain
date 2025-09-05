import json, random, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from grimbrain.engine.progression import proficiency_bonus_for_level, maybe_level_up, award_xp
from grimbrain.engine.loot import roll_loot
from grimbrain.engine.shop import run_shop

def test_pb_table():
    assert proficiency_bonus_for_level(1) == 2
    assert proficiency_bonus_for_level(5) == 3
    assert proficiency_bonus_for_level(9) == 4

def test_xp_award_and_levelup_deterministic():
    pcs = [{"id": "PC1", "name": "Fighter", "level": 1, "xp": 290, "max_hp": 24, "hp": 24, "con_mod": 2, "pb": 2, "prof": 2}]
    gains = award_xp(["Goblin"], pcs, [])
    assert gains["PC1"] == 50
    rng = random.Random(42)
    leveled = maybe_level_up(pcs[0], rng, [])
    assert leveled and pcs[0]["level"] == 2 and pcs[0]["pb"] == 2

def test_loot_gold_and_items():
    rng = random.Random(1)
    notes = []
    loot = roll_loot(["Ogre"], rng, notes)
    assert "gold" in loot and loot["gold"] >= 10

def test_shop_buy_sell_scripted(tmp_path):
    state = {"gold": 60, "inventory": {}}
    script = tmp_path / "shop.txt"
    script.write_text("buy potion_healing\nsell potion_healing\nleave\n")
    notes = []
    run_shop(state, notes, random.Random(3), str(script))
    assert state["gold"] >= 35
