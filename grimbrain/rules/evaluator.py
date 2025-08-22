from __future__ import annotations

import re
from typing import Any, Dict, List, Set, Tuple

from grimbrain.engine import dice
from grimbrain.engine.state import (
    add_death_failure,
    clear_death_saves,
    set_dying,
    set_stable,
)
from grimbrain.config import flag


def _format_expr(expr: str, ctx: Dict[str, Any]) -> str:
    expr = expr.replace("{prof}", str(ctx.get("prof", 0)))
    expr = expr.replace("{dc}", str(ctx.get("dc", 0)))
    mods = ctx.get("mods", {})
    for abil, val in mods.items():
        expr = expr.replace(f"{{mod.{abil}}}", str(val))
    return expr


def _format_tmpl(tmpl: str, ctx: Dict[str, Any]) -> str:
    class AttrDict(dict):
        def __getattr__(self, item):
            return self.get(item, "")

    mapping = {k: AttrDict(v) if isinstance(v, dict) else v for k, v in ctx.items()}
    try:
        return tmpl.format(**mapping)
    except Exception:
        return tmpl


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

    def apply(
        self,
        rule: Dict[str, Any],
        ctx: Dict[str, Any],
        engine=None,
        events: List[Dict[str, Any]] | None = None,
    ) -> List[str]:
        logs: List[str] = []
        effects = rule.get("effects", [])
        log_tmpls = rule.get("log_templates", {})
        if rule.get("dc") is not None:
            ctx.setdefault("dc", rule.get("dc"))
        check_res: Dict[str, Any] = {}
        ctx.setdefault("check", check_res)
        if "start" in log_tmpls:
            logs.append(_format_tmpl(str(log_tmpls["start"]), ctx))
        touched: Set[int] = set()
        start_hp: Dict[int, int] = {}
        dmg_info: Dict[int, Tuple[int, bool]] = {}
        max_hp_map: Dict[int, int] = {}
        for eff in effects:
            when = eff.get("when")
            if when == "check.success" and not ctx.get("check", {}).get("success"):
                continue
            op = eff.get("op")
            target_name = eff.get("target", "target")
            tgt = ctx.get(target_name)
            if tgt is not None:
                tid = id(tgt)
                touched.add(tid)
                prev = tgt.get("hp", 0)
                start_hp.setdefault(tid, prev)
                if tid not in max_hp_map:
                    max_hp_map[tid] = (
                        tgt.get("max_hp")
                        or tgt.get("hp_max")
                        or tgt.get("maxhp")
                        or None
                    )
            if op == "damage" and tgt is not None:
                amount = eval_formula(str(eff.get("amount", 0)), ctx)
                tgt["hp"] = tgt.get("hp", 0) - amount
                ctx["last_amount"] = amount
                ctx["damage_type"] = eff.get("damage_type", ctx.get("damage_type"))
                logs.append(f"{tgt['name']} takes {amount} damage")
                is_crit = "critical" in eff.get("tags", [])
                taken, crit = dmg_info.get(tid, (0, False))
                dmg_info[tid] = (taken + amount, crit or is_crit)
            elif op == "heal" and tgt is not None:
                amount = eval_formula(str(eff.get("amount", 0)), ctx)
                tgt["hp"] = tgt.get("hp", 0) + amount
                ctx["last_amount"] = amount
                logs.append(f"{tgt['name']} heals {amount}")
            elif op is None and engine and tgt is not None and eff.get("duration_rounds"):
                # Timed effect scheduling.  These effects have no "op" field;
                # instead ``duration_rounds`` marks them as timed.  Additional
                # optional keys: ``timing`` (start_of_turn/end_of_turn),
                # ``fixed_damage`` (per-tick), ``tag_add`` and
                # ``tag_remove_on_expire``.
                from grimbrain.effects import TimedEffect

                timing = str(eff.get("timing", "start_of_turn"))
                tag_add = eff.get("tag_add")
                tag_remove = eff.get("tag_remove_on_expire") or tag_add
                fixed = eff.get("fixed_damage")
                count = len(engine.state.get("timed_effects", {}).get(tgt.get("name", ""), []))
                te = TimedEffect(
                    id=f"{rule.get('id','')}:{tgt.get('name','')}:{count}",
                    owner_id=tgt.get("name", ""),
                    source_rule=str(rule.get("id", "")),
                    timing=timing,
                    duration_rounds=int(eff.get("duration_rounds", 0)),
                    remaining_rounds=int(eff.get("duration_rounds", 0)),
                    tag_add=tag_add,
                    tag_remove_on_expire=tag_remove,
                    fixed_damage=int(fixed) if fixed is not None else None,
                    meta={"source": rule.get("id")},
                )
                ev = engine.add_effect(te)
                if events is not None:
                    events.append(ev)
                if tag_add:
                    tags = tgt.setdefault("tags", set())
                    tags.add(tag_add)
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
            elif op == "check" and tgt is not None:
                ability = eff.get("ability", "").upper()
                dc = eval_formula(str(eff.get("dc", 0)), ctx)
                mod = ctx.get("mods", {}).get(ability, 0)
                prof_name = eff.get("proficiency")
                prof_bonus = (
                    ctx.get("prof", 0)
                    if prof_name and prof_name in tgt.get("skills", set())
                    else 0
                )
                tags = tgt.get("tags", set())
                adv = bool(tgt.get("advantage") or ("advantage" in tags))
                disadv = bool(tgt.get("disadvantage") or ("disadvantage" in tags))
                roll = dice.roll("1d20", seed=ctx.get("seed"), adv=adv, disadv=disadv)
                total = roll["total"] + mod + prof_bonus
                ctx["check"]["success"] = total >= dc
                ctx["check"]["total"] = total
                ctx["check"]["dc"] = dc
            elif op == "log":
                tmpl = eff.get("template", "")
                logs.append(_format_tmpl(tmpl, ctx))

        for tid in touched:
            # find actor by id from ctx
            actor = next(
                v for v in ctx.values() if isinstance(v, dict) and id(v) == tid
            )
            prev = start_hp.get(tid, actor.get("hp", 0))
            damage_total, crit = dmg_info.get(tid, (0, False))
            max_hp = (
                max_hp_map.get(tid)
                or actor.get("max_hp")
                or actor.get("hp_max")
                or actor.get("maxhp")
                or 0
            )
            if (
                flag("GB_RULES_INSTANT_DEATH", False)
                and prev > 0
                and (prev - damage_total) <= (-max_hp)
            ):
                actor["hp"] = 0
                actor["dead"] = True
                actor["dying"] = False
                actor["stable"] = False
                clear_death_saves(actor)
                logs.append(
                    f"{actor['name']} suffers catastrophic damage and dies outright."
                )
                continue
            end = actor.get("hp", 0)
            if max_hp:
                actor["hp"] = max(min(end, max_hp), -max_hp)
                end = actor["hp"]
            else:
                actor["hp"] = end
            if prev > 0 and end <= 0:
                actor["hp"] = 0
                set_dying(actor)
                logs.append(f"{actor['name']} drops to 0 HP and is dying.")
            elif prev <= 0 and damage_total > 0:
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
            if prev <= 0 and end > 0:
                clear_death_saves(actor)
                actor["dying"] = False
                actor["stable"] = False
                logs.append(
                    f"{actor['name']} recovers to {actor.get('hp',0)} HP and is no longer dying."
                )
        if check_res.get("success") is not None:
            if check_res.get("success") and log_tmpls.get("apply"):
                logs.append(_format_tmpl(str(log_tmpls["apply"]), ctx))
            elif not check_res.get("success") and log_tmpls.get("fail"):
                logs.append(_format_tmpl(str(log_tmpls["fail"]), ctx))
        else:
            if log_tmpls.get("apply"):
                logs.append(_format_tmpl(str(log_tmpls["apply"]), ctx))
        return logs
