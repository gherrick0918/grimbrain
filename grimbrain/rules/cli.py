from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import List

from grimbrain.content import cli as content_cli
from .resolver import RuleResolver
from .evaluator import Evaluator


def _default_context() -> dict:
    """Return a minimal evaluation context for tests."""
    actor = {"name": "hero", "hp": 10, "advantage": False, "tags": set()}
    target = {"name": "target", "hp": 10, "advantage": False, "tags": set()}
    return {"actor": actor, "target": target, "mods": {"STR": 1}, "prof": 2}


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gb", description="Data-driven rules CLI")
    parser.add_argument("args", nargs="*")
    ns = parser.parse_args(argv)

    rules_dir = os.getenv("GB_RULES_DIR", "rules")
    chroma_dir = os.getenv("GB_CHROMA_DIR", ".chroma")
    resolver = RuleResolver(rules_dir=rules_dir, chroma_dir=chroma_dir)

    if ns.args and ns.args[0] == "rules":
        sub = ns.args[1:]
        if sub and sub[0] == "list":
            return content_cli.main(["list", "--type", "rule"] + sub[1:])
        if sub and sub[0] == "show" and len(sub) >= 2:
            return content_cli.main(["show", f"rule/{sub[1]}"])
        if sub and sub[0] == "reload":
            return content_cli.main(["reload", "--types", "rule"] + sub[1:])
        parser.error("usage: rules [show|reload|list] ...")

    if not ns.args:
        parser.print_help()
        return 0

    verb = ns.args[0]
    target = ns.args[1] if len(ns.args) > 1 else None

    rule, suggestions = resolver.resolve(verb)
    if not rule:
        print("Unknown rule")
        if suggestions:
            print("Suggestions: " + ", ".join(suggestions))
        return 1

    ctx = _default_context()
    ctx["target"] = {
        "name": target or "target",
        "hp": 10,
        "advantage": False,
        "tags": set(),
    }
    ev = Evaluator()
    logs = ev.apply(rule, ctx)
    for line in logs:
        print(line)
    print(json.dumps({"actor_hp": ctx["actor"]["hp"], "target_hp": ctx["target"]["hp"]}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
