from __future__ import annotations

import json
import hashlib
import zipfile
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Dict, List, Tuple, Mapping

from grimbrain.content.ids import canonicalize_id

PersistentClient = None  # type: ignore


class SimpleEmbeddingFunction:
    """Deterministic tiny embedding function for tests."""

    def __call__(self, input: Iterable[str]):  # pragma: no cover - trivial
        vectors: List[List[float]] = []
        for text in input:
            buckets = [0.0] * 32
            for token in text.lower().split():
                h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
                buckets[h % 32] += 1.0
            vectors.append(buckets)
        return vectors

    def name(self) -> str:  # pragma: no cover - trivial
        return "simple"


EMBED_FN = SimpleEmbeddingFunction()


@dataclass
class ContentDoc:
    doc_type: str
    id: str
    name: str
    kind: str | None = ""
    subkind: str | None = ""
    pack: str = ""
    pack_version: str = ""
    payload: Mapping | None = None
    aliases: List[str] | None = None
    metadata: Dict[str, str] | None = None


@dataclass
class IndexResult:
    add: int
    upd: int
    rem: int
    total: int
    by_pack: Dict[str, int]
    by_type: Dict[str, int]
    idx: str


# ---------------------------------------------------------------------------
# helpers

def _slug(name: str) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _slug_dots(name: str) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", ".", name.lower()).strip(".")


def canonical_json(doc: Mapping) -> bytes:
    """Return canonical JSON representation of ``doc``."""

    return json.dumps(doc, sort_keys=True, separators=(",", ":")).encode("utf-8")


def content_signature(doc: Mapping) -> str:
    return hashlib.sha256(canonical_json(doc)).hexdigest()


def index_signature(items: Mapping[Tuple[str, str], str]) -> str:
    payload = json.dumps(
        sorted([(dt, i, sha) for (dt, i), sha in items.items()]),
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:7]


def _normalize_doc(doc: ContentDoc) -> ContentDoc:
    """Normalize ``doc.id`` and collect aliases."""

    raw_id = (doc.id or "").lower()
    canon = canonicalize_id(doc.doc_type, raw_id)
    alias_set = {canonicalize_id(doc.doc_type, a) for a in (doc.aliases or []) if a}
    if raw_id != canon:
        alias_set.add(raw_id)
    alias_set.discard(canon)
    doc.id = canon
    doc.aliases = sorted(alias_set)
    return doc


# ---------------------------------------------------------------------------
# loaders

def load_sources(adapter: str, base_dir: str | Path, packs: List[Path] | None = None) -> Iterable[ContentDoc]:
    base = Path(base_dir)
    packs = packs or []
    if adapter == "rules-json":
        # generated first then custom so custom overrides
        gen_dir = base / "generated"
        if gen_dir.exists():
            for path in sorted(gen_dir.rglob("*.json")):
                try:
                    rule = json.loads(path.read_text())
                except Exception:
                    continue
                rid = rule.get("id") or path.stem
                yield _normalize_doc(
                    ContentDoc(
                        doc_type="rule",
                        id=rid,
                        name=rule.get("name", rid),
                        kind=rule.get("kind"),
                        subkind=rule.get("subkind"),
                        pack="generated",
                        pack_version="",
                        payload=rule,
                        aliases=rule.get("aliases", []),
                        metadata={"source": str(path)},
                    )
                )
        custom_dir = base / "custom"
        src_pack = "custom"
        if custom_dir.exists():
            for path in sorted(custom_dir.rglob("*.json")):
                try:
                    rule = json.loads(path.read_text())
                except Exception:
                    continue
                rid = rule.get("id") or path.stem
                yield _normalize_doc(
                    ContentDoc(
                        doc_type="rule",
                        id=rid,
                        name=rule.get("name", rid),
                        kind=rule.get("kind"),
                        subkind=rule.get("subkind"),
                        pack=src_pack,
                        pack_version="",
                        payload=rule,
                        aliases=rule.get("aliases", []),
                        metadata={"source": str(path)},
                    )
                )
        # flat files fallback
        if not gen_dir.exists() and not custom_dir.exists():
            for path in sorted(base.rglob("*.json")):
                try:
                    rule = json.loads(path.read_text())
                except Exception:
                    continue
                rid = rule.get("id") or path.stem
                yield _normalize_doc(
                    ContentDoc(
                        doc_type="rule",
                        id=rid,
                        name=rule.get("name", rid),
                        kind=rule.get("kind"),
                        subkind=rule.get("subkind"),
                        pack="generated",
                        pack_version="",
                        payload=rule,
                        aliases=rule.get("aliases", []),
                        metadata={"source": str(path)},
                    )
                )
        return

    if adapter == "legacy-data":
        # weapons.json -> rule attack.<weapon>
        wpath = base / "weapons.json"
        if wpath.exists():
            try:
                weapons = json.loads(wpath.read_text())
            except Exception:
                weapons = []
            for w in weapons:
                slug = _slug(w.get("name", ""))
                if not slug:
                    continue
                yield _normalize_doc(
                    ContentDoc(
                        doc_type="rule",
                        id=f"attack.{slug}",
                        name=w.get("name", slug),
                        kind="attack",
                        subkind=w.get("range"),
                        pack="legacy-data",
                        pack_version="",
                        payload=w,
                        aliases=[w.get("name", slug)],
                        metadata={"source": f"virtual:legacy-data/{wpath.name}"},
                    )
                )
        # spells.json -> spell
        spath = base / "spells.json"
        if spath.exists():
            try:
                spells = json.loads(spath.read_text())
            except Exception:
                spells = []
            for s in spells:
                slug = _slug_dots(s.get("name", ""))
                if not slug:
                    continue
                school = s.get("school")
                kind = school.lower() if isinstance(school, str) else None
                subkind = "attack" if s.get("damage_dice") else "utility"
                yield _normalize_doc(
                    ContentDoc(
                        doc_type="spell",
                        id=f"spell.{slug}",
                        name=s.get("name", slug),
                        kind=kind,
                        subkind=subkind,
                        pack="legacy-data",
                        pack_version="",
                        payload=s,
                        aliases=[s.get("name", slug)],
                        metadata={"source": f"virtual:legacy-data/{spath.name}"},
                    )
                )
        # monsters.json -> monster
        mpath = base / "monsters.json"
        if mpath.exists():
            try:
                monsters = json.loads(mpath.read_text())
            except Exception:
                monsters = []
            for m in monsters:
                slug = _slug_dots(m.get("name", ""))
                if not slug:
                    continue
                subkind = m.get("cr") or m.get("size")
                yield _normalize_doc(
                    ContentDoc(
                        doc_type="monster",
                        id=f"monster.{slug}",
                        name=m.get("name", slug),
                        kind=m.get("type"),
                        subkind=subkind,
                        pack="legacy-data",
                        pack_version="",
                        payload=m,
                        aliases=[m.get("name", slug)],
                        metadata={"source": f"virtual:legacy-data/{mpath.name}"},
                    )
                )
        return

    if adapter == "packs":
        def _iter_pack(pack_dir: Path):
            pjson = pack_dir / "pack.json"
            if not pjson.exists():
                return
            try:
                meta = json.loads(pjson.read_text())
            except Exception:
                return
            required = all(isinstance(meta.get(k), str) for k in ("name", "version", "license"))
            if not required:
                return
            pack_name = meta.get("name", pack_dir.name)
            pack_ver = meta.get("version", "")
            for folder in ["rules", "monsters", "spells", "items", "conditions"]:
                sub = pack_dir / folder
                if not sub.exists():
                    continue
                doc_type = folder[:-1]  # plural to singular
                for path in sorted(sub.rglob("*.json")):
                    try:
                        data = json.loads(path.read_text())
                    except Exception:
                        continue
                    slug = _slug_dots(
                        data.get("id") or data.get("name") or path.stem
                    )
                    doc_id = f"{doc_type}.{slug}" if doc_type in {"monster", "spell"} else slug
                    yield _normalize_doc(
                        ContentDoc(
                            doc_type=doc_type,
                            id=doc_id,
                            name=data.get("name", slug),
                            kind=data.get("kind"),
                            subkind=data.get("subkind"),
                            pack=pack_name,
                            pack_version=pack_ver,
                            payload=data,
                            aliases=data.get("aliases", [data.get("name", slug)]),
                            metadata={"source": str(path)},
                        )
                    )

        for src in packs:
            if src.suffix == ".zip":
                try:
                    with zipfile.ZipFile(src) as z, tempfile.TemporaryDirectory() as tmp:
                        z.extractall(tmp)
                        yield from _iter_pack(Path(tmp))
                except Exception:
                    continue
            else:
                yield from _iter_pack(src)
        return

    return []


# ---------------------------------------------------------------------------
# indexing

def incremental_index(
    docs: Iterable[ContentDoc], manifest_path: str | Path, chroma_dir: str | Path
) -> IndexResult:
    manifest_file = Path(manifest_path)
    chroma_path = Path(chroma_dir)
    old_manifest: Dict[str, dict] = {}
    if manifest_file.exists():
        try:
            old_manifest = json.loads(manifest_file.read_text())
        except Exception:
            old_manifest = {}

    # apply precedence based on source
    final_docs: Dict[Tuple[str, str], ContentDoc] = {}

    def _rank(d: ContentDoc) -> int:
        if d.pack == "custom":
            return 3
        if d.pack == "generated":
            return 2
        if d.pack == "legacy-data":
            return 0
        return 1  # packs

    conflicts: Dict[Tuple[str, str], set[str]] = {}

    for doc in docs:
        key = (doc.doc_type, doc.id)
        prev = final_docs.get(key)
        if prev is None:
            final_docs[key] = doc
            continue

        r_prev = _rank(prev)
        r_doc = _rank(doc)
        if r_doc > r_prev or (r_doc == r_prev and prev.pack != doc.pack):
            final_docs[key] = doc
            winner, loser = doc, prev
        else:
            winner, loser = prev, doc

        conflicts.setdefault(key, set()).add(loser.pack)

    for (dt, did), losers in conflicts.items():
        winner_pack = final_docs[(dt, did)].pack
        print(
            f"Conflict: {dt}/{did} -> keeping {winner_pack}, ignoring {', '.join(sorted(losers))}"
        )

    # compute signatures and determine changes
    new_manifest: Dict[str, dict] = {}
    adds = 0
    upds = 0
    by_pack: Dict[str, int] = {}
    by_type: Dict[str, int] = {}
    for (dt, did), doc in final_docs.items():
        sig = content_signature(doc.payload or {})
        by_pack[doc.pack] = by_pack.get(doc.pack, 0) + 1
        by_type[dt] = by_type.get(dt, 0) + 1
        key = f"{dt}/{did}"
        entry = {
            "doc_type": dt,
            "id": did,
            "name": doc.name,
            "pack": doc.pack,
            "kind": doc.kind,
            "subkind": doc.subkind,
            "pack_version": doc.pack_version,
            "sha256": sig,
            "size": len(canonical_json(doc.payload or {})),
            "mtime": 0.0,
            "aliases": doc.aliases or [],
            "payload": doc.payload or {},
        }
        new_manifest[key] = entry
        old = old_manifest.get(key)
        if old is None:
            adds += 1
        elif old.get("sha256") != sig:
            upds += 1

    # removals
    rem_keys = set(old_manifest) - set(new_manifest)
    rems = len(rem_keys)

    # update chroma store
    if PersistentClient is not None:
        client = PersistentClient(path=str(chroma_path))
        collection = client.get_or_create_collection(
            name="content", embedding_function=EMBED_FN
        )
        ids: List[str] = []
        docs_text: List[str] = []
        metas: List[dict] = []
        for (dt, did), doc in final_docs.items():
            key = f"{dt}/{did}"
            old = old_manifest.get(key)
            if old is None or old.get("sha256") != new_manifest[key]["sha256"]:
                ids.append(key)
                docs_text.append(doc.name or did)
                metas.append(
                    {
                        "doc_type": dt,
                        "id": did,
                        "kind": doc.kind,
                        "subkind": doc.subkind,
                        "pack": doc.pack,
                        "pack_version": doc.pack_version,
                        "aliases": json.dumps(doc.aliases or []),
                        "payload": json.dumps(doc.payload or {}),
                    }
                )
        if ids:
            collection.upsert(ids=ids, documents=docs_text, metadatas=metas)
        if rem_keys:
            try:
                collection.delete(ids=list(rem_keys))
            except Exception:
                pass

    # persist manifest
    manifest_file.parent.mkdir(parents=True, exist_ok=True)
    manifest_file.write_text(json.dumps(new_manifest, indent=2))

    # compute idx using new_manifest
    idx = index_signature(
        {tuple(k.split("/")): v["sha256"] for k, v in new_manifest.items()}
    )

    return IndexResult(
        add=adds,
        upd=upds,
        rem=rems,
        total=len(final_docs),
        by_pack=by_pack,
        by_type=by_type,
        idx=idx,
    )
