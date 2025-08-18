from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import List

import jsonschema

from grimbrain.indexing.content_index import load_sources, ContentDoc
from grimbrain.rules.evaluator import eval_formula

RULE_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schema" / "rule.schema.json"
RULE_SCHEMA = json.loads(RULE_SCHEMA_PATH.read_text())

ALLOWED_TOKENS = {"actor.name", "target.name", "last_amount", "damage_type", "rule.id"}


def _validate_doc(doc: ContentDoc) -> str | None:
    data = doc.payload or {}
    try:
        jsonschema.validate(data, RULE_SCHEMA)
    except jsonschema.ValidationError as exc:
        return f"schema: {exc.message}"

    for tmpl in (data.get("log_templates") or {}).values():
        for token in re.findall(r"{([^}]+)}", str(tmpl)):
            t = token.replace("[", ".").replace("]", "")
            if t not in ALLOWED_TOKENS:
                return f"log token {token}"

    exprs: List[str] = []
    for eff in data.get("effects", []):
        amt = eff.get("amount")
        if isinstance(amt, str):
            exprs.append(amt)
    formulas = data.get("formulas", {})
    if isinstance(formulas, dict):
        exprs.extend([str(v) for v in formulas.values() if isinstance(v, (str, int, float))])
    dc = data.get("dc")
    if isinstance(dc, str):
        exprs.append(dc)
    ctx = {
        "mods": {},
        "prof": 0,
        "actor": {"name": ""},
        "target": {"name": ""},
        "last_amount": 0,
        "damage_type": "",
        "rule": {"id": data.get("id", "")},
    }
    for expr in exprs:
        try:
            eval_formula(str(expr), ctx)
        except Exception:
            return f"bad formula {expr}"
    return None


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate rule documents")
    parser.add_argument("--pack", help="Filter by pack name")
    parser.add_argument("--grep", help="Substring filter")
    args = parser.parse_args(argv)

    rules_dir = Path(os.getenv("GB_RULES_DIR", "rules"))
    packs_env = os.getenv("GB_PACKS", "")
    pack_paths = [Path(p) for p in packs_env.split(",") if p]

    docs: List[ContentDoc] = []
    docs.extend(load_sources("rules-json", rules_dir))
    if pack_paths:
        docs.extend(load_sources("packs", Path("."), packs=pack_paths))

    ok = True
    for d in docs:
        if args.pack and d.pack != args.pack:
            continue
        if args.grep and args.grep.lower() not in (d.id + d.name).lower():
            continue
        err = _validate_doc(d)
        if err:
            ok = False
            print(f"ERR {d.id}  {err}")
        else:
            print(f"OK {d.id}")
    return 0 if ok else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
