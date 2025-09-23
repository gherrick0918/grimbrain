import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from grimbrain.engine.inventory import add_item, remove_item, format_inventory
from grimbrain.engine.shop import run_shop


def _contains(texts, needle: str) -> bool:
    return any(needle in entry for entry in texts)


def test_add_remove_and_format():
    inv: dict[str, int] = {}
    add_item(inv, "potion_healing", 2)
    add_item(inv, "ammo_arrows", 10)
    assert inv["potion_healing"] == 2
    formatted = format_inventory(inv)
    assert "potion_healing x2" in formatted
    assert "ammo_arrows x10" in formatted
    ok = remove_item(inv, "potion_healing", 1)
    assert ok and inv["potion_healing"] == 1
    ok = remove_item(inv, "potion_healing", 1)
    assert ok and "potion_healing" not in inv
    assert not remove_item(inv, "ammo_arrows", 20)


def test_run_shop_handles_stack_and_legacy_list(tmp_path):
    state = {"gold": 0, "inventory": ["potion_healing", "potion_healing"]}
    script = tmp_path / "shop.txt"
    script.write_text("sell potion_healing 1\nleave\n")
    notes: list[str] = []
    run_shop(state, notes, random.Random(5), str(script))
    assert state["inventory"].get("potion_healing") == 1
    assert _contains(notes, "Sold potion_healing x1 for 25 gp")
