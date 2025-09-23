
from typing import Dict, List, Optional

from .inventory import add_item, remove_item

PRICES = {"potion_healing": 50, "ammo_arrows": 1, "Longsword": 10, "Scimitar": 10, "Longbow": 10}

def run_shop(state: Dict, notes: List[str], rng, script_path: Optional[str] = None) -> None:
    gold = state.setdefault("gold", 0)
    inv = state.setdefault("inventory", {})
    if isinstance(inv, list):
        normalized: Dict[str, int] = {}
        for item in inv:
            add_item(normalized, item)
        state["inventory"] = inv = normalized
    cmds: List[str] = []
    if script_path:
        with open(script_path, "r", encoding="utf-8") as f:
            cmds = [line.strip() for line in f if line.strip()]
    def buy(item: str, qty: int = 1) -> None:
        nonlocal gold
        price = PRICES.get(item, 0) * qty
        if gold >= price:
            gold -= price
            add_item(inv, item, qty)
            notes.append(f"Bought {item} x{qty} for {price} gp.")
        else:
            notes.append(f"Not enough gold to buy {qty}× {item}.")
    def sell(item: str, qty: int = 1) -> None:
        nonlocal gold
        have = inv.get(item, 0)
        qty = min(qty, have)
        if qty <= 0:
            notes.append(f"No {item} to sell.")
            return
        price = int(PRICES.get(item, 0) * 0.5) * qty
        if not remove_item(inv, item, qty):
            notes.append(f"No {item} to sell.")
            return
        gold += price
        notes.append(f"Sold {item} x{qty} for {price} gp.")
    for raw in cmds:
        parts = raw.split()
        if not parts:
            continue
        op = parts[0].lower()
        if op == "buy" and len(parts) >= 2:
            item = parts[1]
            qty = int(parts[2]) if len(parts) > 2 else 1
            buy(item, qty)
        elif op == "sell" and len(parts) >= 2:
            item = parts[1]
            qty = int(parts[2]) if len(parts) > 2 else 1
            sell(item, qty)
        elif op == "leave":
            break
    state["gold"] = gold
