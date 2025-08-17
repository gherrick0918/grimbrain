from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import List

from grimbrain.indexing.content_index import load_sources, incremental_index, ContentDoc


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

    docs: List[ContentDoc] = []
    if "legacy-data" in adapters:
        docs.extend(load_sources("legacy-data", data_dir))
    if packs:
        docs.extend(load_sources("packs", Path("."), packs=packs))
    if "rules-json" in adapters:
        docs.extend(load_sources("rules-json", rules_dir))

    if types_filter:
        docs = [d for d in docs if d.doc_type in types_filter]

    res = incremental_index(docs, manifest_path, chroma_dir)
    print(
        f"Indexed {res.total} docs (+{res.add} / ~{res.upd} / -{res.rem}) (by_type={res.by_type}, packs={res.by_pack}, idx={res.idx})."
    )
    return 0


def cmd_list(args) -> int:
    chroma_dir = _env_path("GB_CHROMA_DIR", ".chroma")
    manifest = _load_manifest(chroma_dir / "manifest.json")
    for key, entry in sorted(manifest.items()):
        dt = entry.get("doc_type")
        if args.type and dt != args.type:
            continue
        if args.kind and entry.get("kind") != args.kind:
            continue
        if args.pack and entry.get("pack") != args.pack:
            continue
        line = (
            f"{dt}/{entry.get('id')}  "
            f"{entry.get('kind','')}/{entry.get('subkind','')}  "
            f"[{entry.get('pack')}@{entry.get('pack_version','')}]"
        )
        if args.grep and args.grep not in line:
            continue
        print(line)
    return 0


def cmd_show(args) -> int:
    chroma_dir = _env_path("GB_CHROMA_DIR", ".chroma")
    doc_id = args.docid
    if "/" not in doc_id:
        print("format doc_type/id")
        return 1
    dt, did = doc_id.split("/", 1)
    try:
        from chromadb import PersistentClient
    except Exception:
        print("Chroma unavailable")
        return 1
    client = PersistentClient(path=str(chroma_dir))
    try:
        col = client.get_collection("content")
    except Exception:
        print("Not indexed")
        return 1
    try:
        res = col.get(ids=[f"{dt}/{did}"])
    except Exception:
        print("Not found")
        return 1
    metas = res.get("metadatas") or []
    if not metas:
        print("Not found")
        return 1
    payload = metas[0].get("payload")
    if isinstance(payload, str):
        payload = json.loads(payload)
    print(json.dumps(payload, indent=2))
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
    p_reload.set_defaults(func=cmd_reload)

    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
