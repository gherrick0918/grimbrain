from __future__ import annotations

from typing import Dict


def add_item(inv: Dict[str, int], item: str, qty: int = 1) -> None:
    inv[item] = inv.get(item, 0) + qty


def remove_item(inv: Dict[str, int], item: str, qty: int = 1) -> bool:
    current = inv.get(item, 0)
    if current < qty:
        return False
    if current == qty:
        inv.pop(item, None)
    else:
        inv[item] = current - qty
    return True


def format_inventory(inv: Dict[str, int]) -> str:
    if not inv:
        return "(empty)"
    parts = [f"{name} x{amount}" for name, amount in sorted(inv.items())]
    return ", ".join(parts)
