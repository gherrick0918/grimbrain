from __future__ import annotations

import re
from typing import Dict, Any, List, Set, Tuple

from grimbrain.engine import dice
from grimbrain.engine.state import (
    set_dying,
    set_stable,
    clear_death_saves,
    add_death_failure,
)


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
        touched: Set[int] = set()
        start_hp: Dict[int, int] = {}
        dmg_info: Dict[int, Tuple[int, bool]] = {}
        for eff in effects:
            op = eff.get("op")
            target_name = eff.get("target", "target")
            tgt = ctx.get(target_name)
            if tgt is not None:
                tid = id(tgt)
                touched.add(tid)
                start_hp.setdefault(tid, tgt.get("hp", 0))
            if op == "damage" and tgt is not None:
                amount = eval_formula(str(eff.get("amount", 0)), ctx)
                tgt["hp"] = tgt.get("hp", 0) - amount
                logs.append(f"{tgt['name']} takes {amount} damage")
                is_crit = "critical" in eff.get("tags", [])
                taken, crit = dmg_info.get(tid, (0, False))
                dmg_info[tid] = (taken + amount, crit or is_crit)
            elif op == "heal" and tgt is not None:
                amount = eval_formula(str(eff.get("amount", 0)), ctx)
                tgt["hp"] = tgt.get("hp", 0) + amount
                logs.append(f"{tgt['name']} heals {amount}")
            elif op == "clear_death_saves" and tgt is not None:
                clear_death_saves(tgt)
            elif op == "set_stable" and tgt is not None:
                set_stable(tgt)
                logs.append(f"{tgt['name']} is stable at 0 HP.")
            elif op == "set_dying" and tgt is not None:
                set_dying(tgt)
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

        for tid in touched:
            # find actor by id from ctx
            actor = next(v for v in ctx.values() if isinstance(v, dict) and id(v) == tid)
            start = start_hp.get(tid, actor.get("hp", 0))
            end = actor.get("hp", 0)
            dmg, crit = dmg_info.get(tid, (0, False))
            if start > 0 and end <= 0:
                actor["hp"] = 0
                set_dying(actor)
                logs.append(f"{actor['name']} drops to 0 HP and is dying.")
            elif start <= 0 and dmg > 0:
                set_dying(actor)
                actor["stable"] = False
                fails = 2 if crit else 1
                add_death_failure(actor, fails)
                if crit:
                    logs.append(
                        f"Critical hit! {actor['name']} fails two death saves ({actor.get('death_failures',0)}/3)."
                    )
                else:
                    logs.append(
                        f"{actor['name']} takes damage while at 0 HP and fails a death save ({actor.get('death_failures',0)}/3)."
                    )
                if actor.get("dead"):
                    logs.append(f"{actor['name']} dies.")
            if start <= 0 and end > 0:
                clear_death_saves(actor)
                actor["dying"] = False
                actor["stable"] = False
                logs.append(
                    f"{actor['name']} recovers to {actor.get('hp',0)} HP and is no longer dying."
                )
        return logs
