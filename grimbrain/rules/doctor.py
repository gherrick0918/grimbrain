from __future__ import annotations

import os
import re
import time
from collections import defaultdict, namedtuple
from pathlib import Path


Issue = namedtuple("Issue", "severity rule_id field message")

_TOKEN_RE = re.compile(r"\{([^}]+)\}")
_ALLOWED_TOKEN_PREFIXES = (
    "mod.",
    "actor.",
    "target.",
    "spell.",
    "item.",
    "prof",
    "dc",
    "result.",
    "roll.",
)


def parse_formula_local(s: str):
    """Lightweight formula validator."""

    if not isinstance(s, str) or not s.strip():
        return False, "empty formula"
    allowed = re.compile(r"^[0-9dDkK+\-*/().{}_\sA-Za-z]+$")
    if not allowed.match(s):
        return False, "illegal characters"
    return True, None


def validate_tokens_local(text: str, rule: dict):
    unknown = []
    for tok in _TOKEN_RE.findall(text or ""):
        if tok.startswith(_ALLOWED_TOKEN_PREFIXES):
            continue
        if tok in rule.keys():
            continue
        unknown.append(tok)
    return (len(unknown) == 0), unknown


def _load_rules() -> list[dict]:
    try:
        from grimbrain.rules.index import load_rules

        rules_dir = Path(os.getenv("GB_RULES_DIR", "rules"))
        rules, _, _, _ = load_rules(rules_dir)
        return rules
    except Exception:  # pragma: no cover - minimal fallback
        return []


def run_doctor(fail_warn: bool = False) -> int:
    """Audit rule documents and report issues."""

    try:
        rules = _load_rules()
    except Exception as e:
        print(f"Rules Doctor: failed to load rules: {e}")
        return 2

    try:
        from grimbrain.eval import parse_formula as _pf  # type: ignore

        parse_formula = lambda s: _pf(s)
    except Exception:  # pragma: no cover
        parse_formula = parse_formula_local
    try:
        from grimbrain.eval import validate_tokens as _vt  # type: ignore

        validate_tokens = lambda t, r: _vt(t, r)
    except Exception:  # pragma: no cover
        validate_tokens = validate_tokens_local

    t0 = time.perf_counter()
    ids = {r.get("id") for r in rules if r.get("id")}
    aliases: dict[str, list[str]] = defaultdict(list)
    issues: list[Issue] = []

    for r in rules:
        rid = r.get("id", "<missing>")
        for fld in ("dc", "formula", "damage", "heal"):
            val = r.get(fld)
            if not val:
                continue
            ok, err = parse_formula(val)
            if not ok:
                issues.append(Issue("ERROR", rid, fld, f"Bad formula: {err}"))
        if r.get("kind") in ("action", "spell") and not r.get("targets"):
            issues.append(Issue("WARN", rid, "targets", "Missing targets"))
        for eff in r.get("effects", []) or []:
            ref = eff.get("rule_id")
            if ref and ref not in ids:
                issues.append(Issue("ERROR", rid, "effects", f"References unknown rule '{ref}'"))
        tmpl = r.get("log_templates", {}) or {}
        for name, text in tmpl.items():
            ok, bad = validate_tokens(text, r)
            if not ok:
                issues.append(
                    Issue(
                        "WARN",
                        rid,
                        f"log_templates.{name}",
                        f"Unknown tokens: {', '.join(sorted(set(bad)))}",
                    )
                )
        for a in r.get("aliases", []) or []:
            aliases[a].append(rid)

    for a, owners in aliases.items():
        if len(owners) > 1:
            issues.append(
                Issue("ERROR", ",".join(sorted(owners)), "aliases", f"Alias '{a}' maps to multiple rules")
            )

    if issues:
        wsev = max(8, *(len(i.severity) for i in issues))
        wrule = max(8, *(len(i.rule_id) for i in issues))
        wfld = max(10, *(len(i.field) for i in issues))
        print(f"{'SEVERITY':<{wsev}}  {'RULE':<{wrule}}  {'FIELD':<{wfld}}  MESSAGE")
        for i in issues:
            print(f"{i.severity:<{wsev}}  {i.rule_id:<{wrule}}  {i.field:<{wfld}}  {i.message}")
    else:
        print("Rules Doctor: no issues found.")
    dt = (time.perf_counter() - t0) * 1000
    print(f"Scanned {len(rules)} rules in {dt:.1f} ms")

    has_error = any(i.severity == "ERROR" for i in issues)
    has_warn = any(i.severity == "WARN" for i in issues)
    if has_error:
        return 2
    if fail_warn and has_warn:
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - thin wrapper
    import argparse

    parser = argparse.ArgumentParser(description="Audit rules for errors & warnings")
    parser.add_argument("--fail-warn", action="store_true", help="Treat warnings as errors")
    ns = parser.parse_args(argv)
    return run_doctor(fail_warn=ns.fail_warn)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

