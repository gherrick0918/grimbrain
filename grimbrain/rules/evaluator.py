from __future__ import annotations

import re
from typing import Dict, Any, List

from grimbrain.engine import dice


def _format_expr(expr: str, ctx: Dict[str, Any]) -> str:
    expr = expr.replace("{prof}", str(ctx.get("prof", 0)))
    mods = ctx.get("mods", {})
    for abil, val in mods.items():
        expr = expr.replace(f"{{mod.{abil}}}", str(val))
    return expr


def eval_formula(expr: str, ctx: Dict[str, Any]) -> int:
    expr = _format_expr(expr, ctx)
    if re.search(r"\d+d\d+", expr):
        res = dice.roll(expr, seed=ctx.get("seed"))
        return int(res["total"])
    return int(eval(expr, {"__builtins__": {}}, {"min": min, "max": max}))


class Evaluator:
    """Minimal evaluator for data-driven rules."""

    def __init__(self):
        pass

    def apply(self, rule: Dict[str, Any], ctx: Dict[str, Any]) -> List[str]:
        logs: List[str] = []
        effects = rule.get("effects", [])
        for eff in effects:
            op = eff.get("op")
            target_name = eff.get("target", "target")
            tgt = ctx.get(target_name)
            if op == "damage" and tgt is not None:
                amount = eval_formula(str(eff.get("amount", 0)), ctx)
                tgt["hp"] = tgt.get("hp", 0) - amount
                logs.append(f"{tgt['name']} takes {amount} damage")
            elif op == "heal" and tgt is not None:
                amount = eval_formula(str(eff.get("amount", 0)), ctx)
                tgt["hp"] = tgt.get("hp", 0) + amount
                logs.append(f"{tgt['name']} heals {amount}")
            elif op == "tag_add" and tgt is not None:
                tag = eff.get("tag")
                tags = tgt.setdefault("tags", set())
                tags.add(tag)
            elif op == "tag_remove" and tgt is not None:
                tag = eff.get("tag")
                tags = tgt.setdefault("tags", set())
                tags.discard(tag)
            elif op == "advantage_set" and tgt is not None:
                tgt["advantage"] = bool(eff.get("value", True))
            elif op == "log":
                tmpl = eff.get("template", "")
                logs.append(tmpl.format(**ctx))
        return logs
