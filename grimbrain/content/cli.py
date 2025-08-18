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
    if "/" in doc_id:
        dt, did = doc_id.split("/", 1)
    else:
        dt, did = "rule", doc_id

    try:
        from chromadb import PersistentClient
    except Exception:
        print("Chroma unavailable")
        return 1

    client = PersistentClient(path=str(chroma_dir))
    try:
        col = client.get_collection("content")
        res = col.get(ids=[f"{dt}/{did}"])
    except Exception:
        print(f"Not found: {dt}/{did}")
        return 2

    metas = res.get("metadatas") or []
    if not metas:
        print(f"Not found: {dt}/{did}")
        return 2

    payload = metas[0].get("payload")
    if isinstance(payload, str):
        payload = json.loads(payload)
    print(json.dumps(payload, indent=2))
    return 0


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
