from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Tuple, List

from grimbrain.indexing.content_index import load_sources, incremental_index


def load_rules(
    rules_dir: Path,
) -> Tuple[List[dict], int, int, List[tuple[str, int, int]]]:
    """Load rule documents from ``rules_dir``.

    When ``rules_dir`` contains ``generated`` and ``custom`` subdirectories the
    former is loaded first followed by the latter so custom rules override
    generated ones.  The return value is a tuple ``(rules, gen_count, custom_count)``.
    """

    rules: dict[str, dict] = {}
    stats: dict[str, tuple[int, int]] = {}
    gen_count = 0
    custom_count = 0

    gen_dir = rules_dir / "generated"
    custom_dir = rules_dir / "custom"
    if gen_dir.exists():
        for path in sorted(gen_dir.rglob("*.json")):
            try:
                rule = json.loads(path.read_text())
            except Exception as exc:  # pragma: no cover - defensive
                raise RuntimeError(f"Failed loading rule {path}") from exc
            rid = rule.get("id")
            if rid:
                rules[rid] = rule
                s = path.stat()
                stats[rid] = (s.st_size, int(s.st_mtime))
                gen_count += 1
    if custom_dir.exists():
        for path in sorted(custom_dir.rglob("*.json")):
            try:
                rule = json.loads(path.read_text())
            except Exception as exc:  # pragma: no cover - defensive
                raise RuntimeError(f"Failed loading rule {path}") from exc
            rid = rule.get("id")
            if rid:
                rules[rid] = rule  # overrides generated
                s = path.stat()
                stats[rid] = (s.st_size, int(s.st_mtime))
                custom_count += 1

    if not gen_dir.exists() and not custom_dir.exists():
        for path in sorted(rules_dir.rglob("*.json")):
            try:
                rule = json.loads(path.read_text())
            except Exception as exc:  # pragma: no cover - defensive
                raise RuntimeError(f"Failed loading rule {path}") from exc
            rid = rule.get("id")
            if rid:
                rules[rid] = rule
                s = path.stat()
                stats[rid] = (s.st_size, int(s.st_mtime))
        gen_count = len(rules)

    files: List[tuple[str, int, int]] = []
    for rid, rule in rules.items():
        if rid in stats:
            size, mtime = stats[rid]
        else:  # pragma: no cover - future-proof
            size = len(json.dumps(rule, separators=(",", ":")))
            mtime = 0
        files.append((rid, size, mtime))

    return list(rules.values()), gen_count, custom_count, files


def build_index(adapter: str, rules_dir: str | Path, out_dir: str | Path) -> int:
    """Index rules via the generic content indexing helpers."""

    docs = (d for d in load_sources(adapter, rules_dir) if d.doc_type == "rule")
    manifest_path = Path(out_dir) / "manifest.json"
    res = incremental_index(docs, manifest_path, out_dir)
    print(
        f"Indexed {res.total} docs (+{res.add} / ~{res.upd} / -{res.rem}) (by_type={res.by_type}, packs={res.by_pack}, idx={res.idx})."
    )
    return 0


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - thin wrapper
    parser = argparse.ArgumentParser(description="Index grimbrain rules")
    parser.add_argument("--rules", required=True, help="Directory of rule JSON files")
    parser.add_argument(
        "--out", required=True, help="Output directory for Chroma store"
    )
    parser.add_argument(
        "--adapter",
        choices=["rules-json", "legacy-data"],
        default="rules-json",
        help="Content adapter to use",
    )
    args = parser.parse_args(argv)
    return build_index(args.adapter, args.rules, args.out)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
