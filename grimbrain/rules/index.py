from __future__ import annotations

import argparse
import json
import hashlib
from pathlib import Path
from typing import Iterable, Tuple, List

try:  # pragma: no cover - chromadb is heavy but optional for tests
    from chromadb import PersistentClient
    from chromadb.utils import embedding_functions
except Exception:  # pragma: no cover
    PersistentClient = None  # type: ignore
    embedding_functions = None  # type: ignore


class SimpleEmbeddingFunction:
    """Deterministic, tiny embedding function.

    This avoids heavy model downloads while still exercising the vector search
    path in tests.  It is **not** suitable for production quality retrieval but
    suffices for unit tests where we just need a reproducible number sequence.
    """

    def __call__(self, input: Iterable[str]):  # pragma: no cover - tiny utility
        vectors: list[list[float]] = []
        for text in input:
            buckets = [0.0] * 32
            for token in text.lower().split():
                h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
                buckets[h % 32] += 1.0
            vectors.append(buckets)
        return vectors

    # Chroma expects a ``name`` method for persistence metadata.
    def name(self) -> str:  # pragma: no cover - trivial
        return "simple"


EMBED_FN = SimpleEmbeddingFunction()


def _index_signature(files: Iterable[tuple[str, int, int]]) -> str:
    """Return a short digest for the given ``files`` list."""

    payload = json.dumps(sorted(files), separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:7]


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


def build_index(rules_dir: str | Path, out_dir: str | Path) -> int:
    """Index rule JSON files into a persistent Chroma collection."""

    if PersistentClient is None:  # pragma: no cover - chromadb missing
        raise RuntimeError("chromadb is required for rule indexing")

    rules_path = Path(rules_dir)
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    rules, gen_count, custom_count, files = load_rules(rules_path)
    total = len(rules)
    if total == 0:
        print(f'No rules found in "{rules_path}".')
        return 1
    idx = _index_signature(files)

    client = PersistentClient(path=str(out_path))
    # Recreate the collection on every run for determinism
    try:
        client.delete_collection("rules")
    except Exception:
        pass
    collection = client.get_or_create_collection(
        name="rules", embedding_function=EMBED_FN
    )

    docs: list[str] = []
    ids: list[str] = []
    metas: list[dict] = []
    for rule in rules:
        rid = rule.get("id")
        if not rid:
            continue
        ids.append(rid)
        text_parts = [rid, rule.get("cli_verb", ""), " ".join(rule.get("aliases", []))]
        docs.append(" ".join(p for p in text_parts if p))
        meta = {
            "id": rid,
            "kind": rule.get("kind"),
            "cli_verb": rule.get("cli_verb"),
            "aliases": ",".join(rule.get("aliases", [])),
            "subkind": rule.get("subkind"),
            "tags": ",".join(rule.get("tags", [])),
        }
        metas.append(meta)
    if ids:
        collection.upsert(ids=ids, documents=docs, metadatas=metas)

    print(
        f"Indexed {total} rules (generated={gen_count}, custom={custom_count}, idx={idx})."
    )
    return 0


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - thin wrapper
    parser = argparse.ArgumentParser(description="Index grimbrain rules")
    parser.add_argument("--rules", required=True, help="Directory of rule JSON files")
    parser.add_argument(
        "--out", required=True, help="Output directory for Chroma store"
    )
    args = parser.parse_args(argv)
    return build_index(args.rules, args.out)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
