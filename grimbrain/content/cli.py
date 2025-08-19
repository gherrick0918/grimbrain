from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import List

from grimbrain.indexing.content_index import load_sources, incremental_index, ContentDoc
from .watch import Debouncer


def _env_path(name: str, default: str) -> Path:
    return Path(os.getenv(name, default))


def _load_manifest(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return {}
    return {}


def cmd_reload(args) -> int:
    chroma_dir = _env_path("GB_CHROMA_DIR", ".chroma")
    rules_dir = _env_path("GB_RULES_DIR", "rules")
    data_dir = _env_path("GB_DATA_DIR", "data")
    manifest_path = chroma_dir / "manifest.json"

    adapters = args.adapter or ["rules-json", "legacy-data"]
    types_filter = set(args.types.split(",")) if args.types else set()
    packs: List[Path] = []
    if args.packs:
        packs = [Path(p) for p in args.packs.split(",") if p]

    def _run() -> None:
        docs: List[ContentDoc] = []
        if "legacy-data" in adapters:
            docs.extend(load_sources("legacy-data", data_dir))
        if packs:
            docs.extend(load_sources("packs", Path("."), packs=packs))
        if "rules-json" in adapters:
            docs.extend(load_sources("rules-json", rules_dir))

        if types_filter:
            docs[:] = [d for d in docs if d.doc_type in types_filter]

        res = incremental_index(docs, manifest_path, chroma_dir)
        print(
            f"Indexed {res.total} docs (+{res.add} / ~{res.upd} / -{res.rem}) (by_type={res.by_type}, packs={res.by_pack}, idx={res.idx})."
        )

    if not getattr(args, "watch", False):
        _run()
        return 0

    watch_dirs: List[Path] = [rules_dir]
    if "legacy-data" in adapters:
        watch_dirs.append(data_dir)
    watch_dirs.extend(packs)
    watch_dirs = [d for d in watch_dirs if d.exists()]

    deb = Debouncer(_run, wait=0.3)
    _run()

    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer

        class Handler(FileSystemEventHandler):  # pragma: no cover - thin wrapper
            def on_any_event(self, event):
                if event.is_directory:
                    return
                p = Path(getattr(event, "src_path", ""))
                if ".chroma" in p.parts:
                    return
                deb.trigger()

        observer = Observer()
        handler = Handler()
        for d in watch_dirs:
            observer.schedule(handler, str(d), recursive=True)
        observer.start()
        try:
            while True:  # pragma: no cover - loop
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            observer.stop()
            observer.join()
        return 0
    except Exception:
        # polling fallback
        state: dict[str, float] = {}
        for d in watch_dirs:
            for p in d.rglob("*"):
                if p.is_file() and ".chroma" not in p.parts:
                    state[str(p)] = p.stat().st_mtime
        try:
            while True:
                time.sleep(1)
                cur: dict[str, float] = {}
                changed = False
                for d in watch_dirs:
                    for p in d.rglob("*"):
                        if p.is_file() and ".chroma" not in p.parts:
                            m = p.stat().st_mtime
                            cur[str(p)] = m
                            if state.get(str(p)) != m:
                                changed = True
                if set(state) != set(cur):
                    changed = True
                if changed:
                    deb.trigger()
                state = cur
        except KeyboardInterrupt:  # pragma: no cover - simple loop
            return 0


def cmd_list(args) -> int:
    chroma_dir = _env_path("GB_CHROMA_DIR", ".chroma")
    manifest = _load_manifest(chroma_dir / "manifest.json")

    # If only rules are indexed, default to that type for back-compat.
    if not args.type:
        doc_types = {e.get("doc_type") for e in manifest.values()}
        if doc_types == {"rule"}:
            args.type = "rule"

    pattern = args.grep.lower() if args.grep else None
    for _, entry in sorted(manifest.items()):
        dt = entry.get("doc_type")
        if args.type and dt != args.type:
            continue
        if args.kind and entry.get("kind") != args.kind:
            continue
        if args.pack and entry.get("pack") != args.pack:
            continue
        if pattern:
            hay = (entry.get("id", "") + entry.get("name", "")).lower()
            if pattern not in hay:
                continue
        line = (
            f"{dt}/{entry.get('id')}  "
            f"{entry.get('kind','')}/{entry.get('subkind','')}  "
            f"[{entry.get('pack')}@{entry.get('pack_version','')}]"
        )
        print(line)
    return 0


def cmd_show(args) -> int:
    chroma_dir = _env_path("GB_CHROMA_DIR", ".chroma")
    doc_id = args.docid
    explicit_dt = "/" in doc_id
    if explicit_dt:
        dt, did = doc_id.split("/", 1)
    else:
        dt, did = "rule", doc_id

    from difflib import SequenceMatcher
    from grimbrain.content.ids import canonicalize_id

    manifest = _load_manifest(Path(chroma_dir) / "manifest.json")

    # Build alias and id maps for the requested doc_type
    alias_map: dict[str, str] = {}
    id_map: dict[str, dict] = {}
    for entry in manifest.values():
        if entry.get("doc_type") != dt:
            continue
        cid = str(entry.get("id", ""))
        alias_map[cid.lower()] = cid
        id_map[cid] = entry
        for a in entry.get("aliases", []) or []:
            alias_map[str(a).lower()] = cid

    canon = canonicalize_id(dt, did)
    entry = id_map.get(canon)
    if entry is not None:
        print(json.dumps(entry.get("payload"), indent=2))
        return 0

    alias_target = alias_map.get(did.lower())
    if alias_target:
        entry = id_map.get(alias_target)
        if entry is not None:
            print(json.dumps(entry.get("payload"), indent=2))
            return 0

    # Suggestions
    query = did.lower()
    suggestions: List[str] = []
    if dt == "rule" and not explicit_dt:
        verb_map: dict[str, str] = {}
        for entry in id_map.values():
            rule = entry.get("payload") or {}
            verb = rule.get("cli_verb")
            if verb:
                verb_map[verb.lower()] = verb
                for a in rule.get("aliases", []) or []:
                    verb_map[str(a).lower()] = verb
        scored: List[tuple[int, int, float, str]] = []
        for alias, canon in verb_map.items():
            start = 1 if alias.startswith(query) else 0
            sub = 1 if query in alias else 0
            ratio = SequenceMatcher(None, query, alias).ratio()
            scored.append((start, sub, ratio, canon))
        scored.sort(key=lambda x: (-x[0], -x[1], -x[2]))
        seen: set[str] = set()
        for _, _, _, canon in scored:
            if canon not in seen:
                seen.add(canon)
                suggestions.append(canon)
            if len(suggestions) >= 10:
                break
        print(f'Not found verb: "{did}"')
        if suggestions:
            print("Did you mean: " + ", ".join(suggestions))
        return 2
    else:
        scored: List[tuple[int, int, float, str]] = []
        for alias, cid in alias_map.items():
            start = 1 if alias.startswith(query) else 0
            sub = 1 if query in alias else 0
            ratio = SequenceMatcher(None, query, alias).ratio()
            scored.append((start, sub, ratio, cid))
        scored.sort(key=lambda x: (-x[0], -x[1], -x[2]))
        seen: set[str] = set()
        for _, _, _, cid in scored:
            if cid not in seen:
                seen.add(cid)
                suggestions.append(cid)
            if len(suggestions) >= 10:
                break

        print(f"Not found: {dt}/{did}")
        if suggestions:
            print("Did you mean: " + ", ".join(f"{dt}/{s}" for s in suggestions))
        return 2


def cmd_packs(_args) -> int:
    chroma_dir = _env_path("GB_CHROMA_DIR", ".chroma")
    manifest = _load_manifest(chroma_dir / "manifest.json")
    counts: dict[str, int] = {}
    versions: dict[str, str] = {}
    for entry in manifest.values():
        pack = entry.get("pack", "")
        if not pack:
            continue
        counts[pack] = counts.get(pack, 0) + 1
        versions.setdefault(pack, entry.get("pack_version", ""))
    for pack, count in sorted(counts.items()):
        ver = versions.get(pack, "")
        suffix = f"@{ver}" if ver else ""
        print(f"{pack}{suffix}: {count}")
    return 0


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="content")
    sub = parser.add_subparsers(dest="cmd")

    p_list = sub.add_parser("list")
    p_list.add_argument("--type")
    p_list.add_argument("--kind")
    p_list.add_argument("--pack")
    p_list.add_argument("--grep")
    p_list.set_defaults(func=cmd_list)

    p_show = sub.add_parser("show")
    p_show.add_argument("docid")
    p_show.set_defaults(func=cmd_show)

    p_reload = sub.add_parser("reload")
    p_reload.add_argument("--adapter", action="append")
    p_reload.add_argument("--packs")
    p_reload.add_argument("--types")
    p_reload.add_argument("--watch", action="store_true")
    p_reload.set_defaults(func=cmd_reload)

    p_packs = sub.add_parser("packs")
    p_packs.set_defaults(func=cmd_packs)

    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
