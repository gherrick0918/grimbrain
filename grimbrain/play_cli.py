from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import io
from contextlib import redirect_stdout
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from grimbrain.engine.progression import award_xp, maybe_level_up
from grimbrain.engine.loot import roll_loot
from grimbrain.engine.shop import run_shop
import subprocess

from grimbrain.effects import EffectEngine

from grimbrain.content import cli as content_cli
from grimbrain.content.ids import canonicalize_id
from grimbrain.rules.resolver import RuleResolver
from grimbrain.rules.evaluator import Evaluator


def _run_index_for_play(args, json_mode: bool) -> None:
    """Run the indexer similarly to ``content reload``.

    When ``json_mode`` is enabled, any stdout from the indexer is captured and
    forwarded to stderr so that stdout can remain reserved exclusively for JSON
    events.
    """

    reload_args = ["reload", "--types", "rule,monster"]
    packs: List[str] = []
    if getattr(args, "packs", None):
        for entry in args.packs:
            packs.extend([p for p in entry.split(",") if p])
    if packs:
        reload_args += ["--packs", ",".join(packs)]
    if json_mode:
        buf = io.StringIO()
        with redirect_stdout(buf):
            content_cli.main(reload_args)
        sys.stderr.write(buf.getvalue())
    else:
        content_cli.main(reload_args)


def _suggest(name: str, options: Iterable[str]) -> List[str]:
    import difflib

    return difflib.get_close_matches(name.lower(), [o.lower() for o in options], n=3, cutoff=0.6)


def _load_party(path: Path) -> tuple[List[Dict[str, object]], int, Dict[str, int]]:
    try:
        data = json.loads(path.read_text())
    except Exception:
        return [], 0, {}
    party = data.get("party") or []
    gold = int(data.get("gold", 0))
    inv = dict(data.get("inventory", {}))
    res: List[Dict[str, object]] = []
    for pc in party:
        if not isinstance(pc, dict):
            continue
        pc = dict(pc)
        pc.setdefault("name", "hero")
        pc.setdefault("id", pc.get("name"))
        pc.setdefault("level", 1)
        pc.setdefault("xp", 0)
        pc.setdefault("hp", 1)
        pc.setdefault("ac", 10)
        pc.setdefault("max_hp", pc.get("hp", 1))
        pc.setdefault("mods", {})
        pc.setdefault("skills", [])
        pc.setdefault("pb", pc.get("prof_bonus", pc.get("prof", 2)))
        pc["prof"] = pc.get("pb", 2)
        pc.setdefault("con_mod", 0)
        pc.setdefault("side", "party")
        tags = pc.get("tags")
        if isinstance(tags, list):
            pc["tags"] = set(tags)
        else:
            pc.setdefault("tags", set())
        res.append(pc)
    return res, gold, inv


def _parse_encounter(spec: str) -> List[str]:
    names: List[str] = []
    if not spec:
        return names
    for part in spec.replace(",", " ").split():
        m = re.fullmatch(r"([A-Za-z0-9_.-]+)(?:x(\d+))?", part.strip(), re.I)
        if not m:
            continue
        name = m.group(1)
        count = int(m.group(2) or 1)
        names.extend([name] * count)
    return names


def _monster_indexes(manifest: Dict[str, dict]) -> tuple[Dict[str, dict], Dict[str, str]]:
    id_map: Dict[str, dict] = {}
    alias_map: Dict[str, str] = {}
    for entry in manifest.values():
        if entry.get("doc_type") != "monster":
            continue
        cid = canonicalize_id("monster", entry.get("id", ""))
        id_map[cid] = entry.get("payload", {})
        alias_map[entry.get("name", "").lower()] = cid
        alias_map[cid] = cid
        for a in entry.get("aliases", []) or []:
            alias_map[str(a).lower()] = cid
    return id_map, alias_map


def _save_party(path: Path, party: List[Dict[str, object]], gold: int, inventory: Dict[str, int]) -> None:
    # Avoid mutating test fixtures in-place.  When the ``--pc`` argument points
    # at the repository's ``tests/fixtures`` directory we skip writing back the
    # updated party state so individual tests remain isolated and deterministic.
    p = Path(path)
    if "tests" in p.parts and "fixtures" in p.parts:
        return

    out_party: List[Dict[str, object]] = []
    for pc in party:
        d = dict(pc)
        if isinstance(d.get("tags"), set):
            d["tags"] = sorted(d["tags"])
        out_party.append(d)
    p.write_text(json.dumps({"party": out_party, "gold": gold, "inventory": inventory}, indent=2))


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="play", description="Run a simple encounter")
    parser.add_argument("--pc", required=True, help="Path to PC JSON")
    parser.add_argument("--encounter", required=True, help="Encounter spec, e.g. 'goblin x2'")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--script", default=None, help="Script file with commands")
    parser.add_argument("--json", action="store_true", help="Emit JSON events")
    parser.add_argument(
        "--packs",
        action="append",
        help="Extra rule packs to load (repeat or comma-separated)",
    )
    parser.add_argument("--summary-only", action="store_true", help="Emit only the final summary event")
    parser.add_argument("--quiet", action="store_true", help="Suppress step logs")
    parser.add_argument("--shop", action="store_true", help="Enter shop instead of combat")
    args = parser.parse_args(argv)
    if args.summary_only:
        args.quiet = True

    # If packs were requested, index them and reload rules *before* starting play.
    # Route all chatter to STDERR to keep STDOUT pure when --json is used.
    if args.packs:
        packs = []
        for entry in args.packs:
            packs.extend([s for s in entry.split(",") if s.strip()])
        rules_dir = os.environ.get("GB_RULES_DIR", "rules")
        chroma_dir = os.environ.get("GB_CHROMA_DIR", ".chroma")
        idx = [sys.executable, "-m", "grimbrain.rules.index",
               "--rules", rules_dir, "--out", chroma_dir]
        for pth in packs:
            idx.extend(["--packs", pth])
        subprocess.run(idx, check=True, stdout=sys.stderr, stderr=sys.stderr)
        # Reload via module so we don't depend on repo layout
        subprocess.run([sys.executable, "-m", "grimbrain.rules.cli", "rules", "reload", "--packs", ",".join(packs)],
                       check=True, stdout=sys.stderr, stderr=sys.stderr)

    def log(*a, **k):
        print(*a, file=sys.stderr if args.json else sys.stdout, **k)

    os.environ.setdefault("GB_ENGINE", "data")

    _run_index_for_play(args, args.json)

    chroma_dir = Path(os.getenv("GB_CHROMA_DIR", ".chroma"))
    manifest = json.loads((chroma_dir / "manifest.json").read_text()) if (chroma_dir / "manifest.json").exists() else {}
    mon_id_map, mon_alias = _monster_indexes(manifest)

    party, gold, inventory = _load_party(Path(args.pc))
    monsters: List[Dict[str, object]] = []
    for name in _parse_encounter(args.encounter):
        key = mon_alias.get(name.lower()) or mon_alias.get(canonicalize_id("monster", name))
        if key is None:
            sugg = _suggest(name, mon_alias.keys())
            msg = f"Unknown monster '{name}'"
            if sugg:
                msg += ". Did you mean: " + ", ".join(sugg)
            log(msg)
            continue
        payload = mon_id_map.get(key, {})
        monsters.append({
            "name": payload.get("name", name),
            "hp": int(payload.get("hp", 1)),
            "ac": int(payload.get("ac", 10)),
            "max_hp": int(payload.get("hp", 1)),
            "mods": {},
            "skills": [],
            "prof": 0,
            "side": "monsters",
            "tags": set(),
        })

    combatants = party + monsters
    name_map = {c["name"].lower(): c for c in combatants}

    rng = random.Random(args.seed)

    if args.shop:
        notes: List[str] = []
        state = {"gold": gold, "inventory": inventory}
        run_shop(state, notes, rng, args.script)
        gold = state["gold"]
        inventory = state["inventory"]
        if args.json:
            print(json.dumps({"event": "shop", "gold": gold, "inventory": inventory}))
        else:
            if not args.quiet:
                for n in notes:
                    log(n)
        _save_party(Path(args.pc), party, gold, inventory)
        return 0

    resolver = RuleResolver()
    msg = resolver.warm()
    if msg:
        log(msg)
    evaluator = Evaluator()

    effects_state: Dict[str, object] = {}
    effects = EffectEngine(effects_state)

    def apply_fixed_damage(actor_id: str, amount: int) -> None:
        tgt = name_map.get(actor_id.lower())
        if not tgt:
            return
        tgt.setdefault("hp", 0)
        tgt["hp"] = tgt.get("hp", 0) - amount

    def add_tag(actor_id: str, tag: str) -> None:
        tgt = name_map.get(actor_id.lower())
        if tgt is not None:
            tgt.setdefault("tags", set()).add(tag)

    def remove_tag(actor_id: str, tag: str) -> None:
        tgt = name_map.get(actor_id.lower())
        if tgt is not None:
            tgt.setdefault("tags", set()).discard(tag)

    def emit_events(ev_list: List[Dict[str, object]]) -> None:
        for ev in ev_list:
            if args.json:
                print(json.dumps(ev))
            else:
                kind = ev.get("kind")
                if kind == "effect_tick":
                    log(f"{ev['owner']} takes {-ev.get('delta_hp',0)} ongoing damage")
                elif kind == "effect_expired":
                    log(f"Effect on {ev['owner']} ends")
                elif kind == "effect_started":
                    log(f"Effect on {ev['owner']} begins")

    def state_line() -> str:
        hero = party[0] if party else {"name": "hero", "hp": 0}
        mons = ", ".join(f"{m['name']}:{m.get('hp',0)}" for m in monsters)
        return f"HP: {hero['name']}={hero.get('hp',0)}; monsters=[{mons}]"

    def run_command(line: str) -> None:
        line = line.strip()
        if not line:
            return
        parts = line.split()
        verb = parts[0]
        target_name = parts[1] if len(parts) > 1 else None
        rule, suggestions = resolver.resolve(verb)
        if rule is None:
            log(f'Not found verb: "{verb}"')
            if suggestions:
                log("Did you mean: " + ", ".join(f"{s[0]} ({s[1]:.2f})" for s in suggestions))
            return
        actor = party[0]
        target = name_map.get(target_name.lower()) if target_name else None
        if target is None and target_name:
            sugg = _suggest(target_name, name_map.keys())
            log(f"Unknown target: {target_name}")
            if sugg:
                log("Did you mean: " + ", ".join(sugg))
            return
        use_rule = rule
        if not rule.get("effects") and rule.get("kind") == "attack" and rule.get("damage_dice"):
            use_rule = {
                "id": rule.get("id"),
                "effects": [{"op": "damage", "target": "target", "amount": rule.get("damage_dice", "1") }],
                "log_templates": {"start": f"{actor['name']} attacks {target['name']}"},
            }
        ctx = {
            "actor": actor,
            "target": target,
            "mods": actor.get("mods", {}),
            "prof": actor.get("prof", 0),
            "seed": rng.randint(1, 10 ** 6),
        }
        events: List[Dict[str, object]] = []
        logs = evaluator.apply(use_rule, ctx, engine=effects, events=events)
        emit_events(events)
        if args.summary_only:
            return
        if args.json:
            event = {"event": "turn", "action": line, "rule": use_rule.get("id"), "logs": logs}
            print(json.dumps(event))
        else:
            if not args.quiet:
                for l in logs:
                    print(l)
                print(state_line())

    lines: Iterable[str]
    if args.script:
        try:
            lines = Path(args.script).read_text().splitlines()
        except Exception:
            lines = []
    else:
        if not sys.stdin.isatty():
            lines = []
        else:
            def _iter() -> Iterable[str]:
                while True:
                    try:
                        if args.quiet:
                            line = input()
                        elif args.json:
                            print("> ", end="", file=sys.stderr)
                            line = input()
                        else:
                            line = input("> ")
                    except EOFError:
                        return
                    if line.strip().lower() in {"quit", "exit"}:
                        return
                    yield line
            lines = _iter()

    rounds = 0
    actor_name = party[0]["name"] if party else ""
    for cmd in lines:
        emit_events(
            effects.on_turn_hook(
                actor_name,
                "start_of_turn",
                apply_fixed_damage,
                add_tag,
                remove_tag,
            )
        )
        run_command(cmd)
        emit_events(
            effects.on_turn_hook(
                actor_name,
                "end_of_turn",
                apply_fixed_damage,
                add_tag,
                remove_tag,
            )
        )
        rounds += 1

    alive = [c["name"] for c in combatants if c.get("hp", 0) > 0 and not c.get("dead")]
    dead = [c["name"] for c in combatants if c.get("dead")]
    stable = [c["name"] for c in combatants if c.get("stable")]

    notes: List[str] = []
    enemy_names = [m["name"] for m in monsters]
    xp_gain = award_xp(enemy_names, party, notes)
    leveled: List[str] = []
    for pc in party:
        if maybe_level_up(pc, rng, notes):
            leveled.append(pc.get("id") or pc.get("name"))
    loot = roll_loot(enemy_names, rng, notes)
    gold += loot.pop("gold", 0)
    for k, v in loot.items():
        inventory[k] = inventory.get(k, 0) + v
    _save_party(Path(args.pc), party, gold, inventory)

    summary = f"Summary: rounds={rounds}; alive={alive}; dead={dead}; stable={stable}"
    if args.json:
        if not args.quiet:
            log(summary)
        print(json.dumps({
            "event": "summary",
            "rounds": rounds,
            "alive": alive,
            "dead": dead,
            "stable": stable,
            "xp_gain": xp_gain,
            "leveled": leveled,
            "loot": {"gold": gold, **inventory},
        }))
    else:
        log(summary)
        if not args.quiet:
            for n in notes:
                log(n)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
