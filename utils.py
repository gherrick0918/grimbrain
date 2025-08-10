"""
utils.py — shared helpers for retrieval, formatting, and debug logging.

Design goals
- 100% local: never requires OpenAI.
- Backwards compatible: keep function names and call signatures stable.
- Defensive: tolerate different LlamaIndex/Chroma versions at runtime.
"""

from __future__ import annotations

import inspect
import os
import re
import sys
from typing import Any, Iterable, Optional
# PATCH: Add extra types for patch helpers
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union, Callable, Union
import os
import re
from pathlib import Path  # <-- Add this import at the top of the file

# -----------------------------------------------------------------------------
# Logging & text helpers
# -----------------------------------------------------------------------------

def _log(msg: str) -> None:
    """Lightweight stderr logger that never crashes on encoding."""
    try:
        print(msg, file=sys.stderr, flush=True)
    except Exception:
        sys.stderr.write((msg or "") + "\n")
        sys.stderr.flush()


TAG_RE = re.compile(r"\{@[^}]+\}")                   # e.g., {@atk mw}, {@dc 15}
BOLD_RE = re.compile(r"\*\*(.*?)\*\*")               # **bold**
ITALIC_RE = re.compile(r"_(.*?)_")                   # _italic_


def strip_markup(text: str) -> str:
    """
    Remove 5eTools-style inline tags and basic markdown emphasis from a string.
    Useful when you need a plain-text version for scoring or previews.
    """
    if not text:
        return ""
    out = TAG_RE.sub("", text)
    out = BOLD_RE.sub(r"\1", out)
    out = ITALIC_RE.sub(r"\1", out)
    # Collapse repeated whitespace
    out = re.sub(r"[ \t]+", " ", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def normalize_name(name: str) -> str:
    """
    Normalize entity names for matching: lowercase, trimmed, collapse spaces.
    """
    if not name:
        return ""
    n = strip_markup(name).lower()
    n = re.sub(r"\s+", " ", n).strip()
    n = n.strip("()[]{}:;,.")  # Remove surrounding punctuation some sources include
    return n


def fmt_sources(sources: Iterable[str] | None) -> str:
    """Render a simple 'Sources considered' footer line."""
    if not sources:
        return ""
    parts = [s for s in sources if s]
    if not parts:
        return ""
    return f"_Sources considered:_ " + " · ".join(parts)


# -----------------------------------------------------------------------------
# Small general-purpose utils (back-compat with older codepaths)
# -----------------------------------------------------------------------------

def coerce_obj(value: Any, default_key: str = "text") -> dict:
    """
    Convert arbitrary input into a dict.  Old formatters call this to be able
    to uniformly read fields whether the source provided a plain string,
    a list/tuple, or a mapping.

    Examples:
      coerce_obj("Fireball")           -> {"text": "Fireball"}
      coerce_obj(["a","b"])            -> {"text": ["a","b"]}
      coerce_obj({"name":"Fireball"})  -> {"name":"Fireball"}  (passthrough)
      coerce_obj(None)                 -> {}
    """
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, (list, tuple)):
        return {default_key: list(value)}
    return {default_key: value}


def ordinal(n: int) -> str:
    """
    Return the ordinal string for an integer: 1 -> '1st', 2 -> '2nd', etc.
    Handles negatives and large values. Non-ints are coerced if possible.
    """
    try:
        n = int(n)
    except Exception:
        # If coercion fails, just return the input as string
        return str(n)
    s = abs(n) % 100
    if 11 <= s <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(abs(n) % 10, "th")
    return f"{n}{suffix}"


# -----------------------------------------------------------------------------
# Hit extraction helpers
# -----------------------------------------------------------------------------

def hit_text(hit: Any) -> str:
    """
    Return user-facing text content from a retrieval 'hit'. Handles common
    LlamaIndex node types as well as raw dicts/strings.

    Accepts:
      - NodeWithScore
      - TextNode / BaseNode
      - dicts with 'text' / 'content'
      - raw strings
    """
    try:
        # LlamaIndex NodeWithScore
        node = hit.node if hasattr(hit, "node") else hit

        # Newer LlamaIndex nodes expose get_content()
        if hasattr(node, "get_content") and callable(node.get_content):
            return node.get_content() or ""

        # Older nodes
        if hasattr(node, "text"):
            return node.text or ""

        # A dict from a custom pipeline
        if isinstance(node, dict):
            for k in ("text", "content", "body"):
                if k in node and isinstance(node[k], str):
                    return node[k]

        # Fallbacks
        if isinstance(node, str):
            return node
        return str(node)
    except Exception as e:
        _log(f"⚠️ hit_text fallback due to: {e}")
        try:
            return str(hit)
        except Exception:
            return ""


# -----------------------------------------------------------------------------
# Chroma collection utilities
# -----------------------------------------------------------------------------

# PATCH: Import EmbeddingFunction for ChromaEFWrapper base class
try:
    from chromadb.utils.embedding_functions import EmbeddingFunction
except ImportError:
    class EmbeddingFunction:
        pass

class ChromaEFWrapper(EmbeddingFunction):
    def __init__(self, model):
        self.model = model

    # Chroma looks at this when comparing persisted EF config
    def name(self) -> str:
        # 'default' avoids conflicts with previously created collections
        return "default"

    # PATCH: Add get_config for newer chroma
    def get_config(self) -> dict:
        return {"name": self.name(), "type": "known", "config": {}}

    # Some versions *call* this; provide a method (not a bool attr)
    def is_legacy(self) -> bool:
        return False

    def __call__(self, input):  # <- exact param name Chroma checks
        # Normalize to list[str]
        if isinstance(input, str):
            batch = [input]
        else:
            batch = list(input)

        # Try common embedder APIs
        if hasattr(self.model, "get_text_embedding_batch"):
            return self.model.get_text_embedding_batch(batch)
        if hasattr(self.model, "embed_documents"):
            return self.model.embed_documents(batch)
        if hasattr(self.model, "embed"):
            return [self.model.embed(t) for t in batch]
        if hasattr(self.model, "get_text_embedding"):
            return [self.model.get_text_embedding(t) for t in batch]

        raise RuntimeError("Provided embedder is not callable by Chroma.")

    def __repr__(self) -> str:
        cls = type(self.model).__name__
        return f"<ChromaEFWrapper name={self.name()} model={cls}>"


def _maybe_wrap_embedding_function(embedder: Any):
    """
    Wrap a LlamaIndex/HF embedder so it can be used as a Chroma embedding_function.
    Chroma expects:
      - .__call__(self, input) -> list[list[float]]  (note param name 'input')
      - .name() -> str
      - optionally .is_legacy() -> bool
    """
    if embedder is None:
        return None
    return ChromaEFWrapper(embedder)

def ensure_collection(client: Any, name: str, embedder: Any | None = None):
    """
    Create or fetch a Chroma collection safely across versions.

    Signature kept as (client, name, embedder=None) to match existing imports.
    The 'embedder' is optional and ignored unless your Chroma build expects
    an embedding_function on the collection itself.

    Returns:
        A Chroma collection object ready to be wrapped in ChromaVectorStore.
    """
    if client is None:
        raise ValueError("ensure_collection: 'client' must not be None")
    if not name:
        raise ValueError("ensure_collection: 'name' must be a non-empty string")

    fn = getattr(client, "get_or_create_collection", None)
    if not callable(fn):
        raise RuntimeError("Client does not expose get_or_create_collection")

    # Build kwargs compatibly with whatever this chroma version supports
    sig = inspect.signature(fn)
    kwargs = {}
    if "metadata" in sig.parameters:
        kwargs["metadata"] = {"owner": "grimbrain", "kind": "index"}
    if "embedding_function" in sig.parameters and embedder is not None:
        kwargs["embedding_function"] = _maybe_wrap_embedding_function(embedder)

    try:
        collection = fn(name, **kwargs)
    except AttributeError as e:
        # If Chroma complains about EF metadata, retry without EF
        if "name" in str(e) or "is_legacy" in str(e):
            collection = fn(name)  # clean retry
        else:
            raise
    except TypeError:
        collection = fn(name)  # fallback for older signatures

    # Sanity check for API we rely on (.get/.add)
    for attr in ("get", "add"):
        if not hasattr(collection, attr):
            _log(f"⚠️ Collection missing expected method '{attr}' on '{name}'")

    return collection


# -----------------------------------------------------------------------------
# Name scoring (kept for compatibility — some older routes import these)
# -----------------------------------------------------------------------------

def score_name_match(query: str, candidate: str) -> float:
    """
    Heuristic name score used to bias exact or token-prefix matches.
    Higher is better. Purely deterministic, no embeddings required.
    """
    if not query or not candidate:
        return 0.0
    q = normalize_name(query)
    n = normalize_name(candidate)

    if q == n:
        return 100.0
    if n.startswith(q + " "):
        return 60.0
    if q in n.split():
        return 40.0

    # Shared token overlap bonus
    qtok = set(q.split())
    ntok = set(n.split())
    inter = len(qtok & ntok)
    if inter:
        return 10.0 + inter * 2.0

    # Mild fuzzy bonus for prefix
    if n.startswith(q):
        return 5.0

    return 0.0


def best_name_match(query: str, names: Iterable[str]) -> Optional[str]:
    """Return the single best name from a list for a given query."""
    best = None
    best_s = float("-inf")
    for cand in names or []:
        s = score_name_match(query, cand)
        if s > best_s:
            best_s = s
            best = cand
    return best


# -----------------------------------------------------------------------------
# Lightweight provenance builder
# -----------------------------------------------------------------------------

def sources_from_nodes(nodes: Iterable[Any]) -> list[str]:
    """
    Extract human-readable source labels from LlamaIndex nodes/hits.
    We look at common metadata keys but never fail if they’re absent.
    """
    out: list[str] = []
    for h in nodes or []:
        node = getattr(h, "node", h)
        meta = getattr(node, "metadata", None)
        if isinstance(meta, dict):
            src = (
                meta.get("source")
                or meta.get("doc_id")
                or meta.get("file_name")
                or meta.get("dataset")
            )
            if src:
                out.append(str(src))
    # De-dupe while preserving order
    seen = set()
    uniq = []
    for s in out:
        if s not in seen:
            seen.add(s)
            uniq.append(s)
    return uniq


# -----------------------------------------------------------------------------
# JSON root key inference
# -----------------------------------------------------------------------------

__all__ = [
    # ...existing exports...
    "infer_root_key",
    "resolve_copy",
    "stamp_doc_meta",
]

def infer_root_key(
    data: dict,
    preferred: Optional[str] = None,
    filename: Optional[str] = None,
) -> str:
    """
    Guess the primary 5eTools-like root key for a loaded JSON file.
    Heuristics:
      1) If `preferred` is provided and present in the data, use it.
      2) If `filename` hints at a known key (e.g., "bestiary", "spells"), use that.
      3) Use the first known key present (monster, spell, item, etc.).
      4) Use the first list-of-dicts-with-name key.
      5) Fallback to the first key in the dict or "data".
    """
    if not isinstance(data, dict) or not data:
        return "data"

    # 1) explicit preference
    if preferred and preferred in data:
        return preferred

    # 2) filename hints
    hint = (os.path.basename(filename).lower() if filename else "")
    hint_map = {
        r"bestiary|monster": "monster",
        r"\bspells?\b": "spell",
        r"\bitems?\b": "item",
        r"\braces?\b": "race",
        r"\bbackgrounds?\b": "background",
        r"\bfeats?\b": "feat",
        r"\bclasses?\b": "class",
        r"\bsubclasses?\b": "subclass",
        r"\bopt(ional)?features?\b": "optionalfeature",
    }
    if hint:
        for pat, key in hint_map.items():
            if re.search(pat, hint):
                if key in data:
                    return key

    # 3) known primary keys commonly used by 5eTools-style JSON
    known_keys = (
        "monster",
        "spell",
        "item",
        "class",
        "subclass",
        "race",
        "background",
        "feat",
        "optionalfeature",
        "vehicle",
        "trap",
        "hazard",
        "object",
        "deity",
        "variant",
        "book",
        "adventure",
    )
    for k in known_keys:
        if k in data and isinstance(data[k], list) and data[k]:
            return k

    # 4) any list of dicts with a 'name' field
    for k, v in data.items():
        if isinstance(v, list) and v and isinstance(v[0], dict) and ("name" in v[0] or "id" in v[0]):
            return k

    # 5) last resort
    return next(iter(data.keys()), "data")

# ------------------------------- 5eTools copy/patch helpers -------------------------------

def _coalesce(*keys: str, in_dict: Dict[str, Any]) -> Optional[Any]:
    """Return the first present value among misspelling variants (e.g., items/itemss/iteems)."""
    for k in keys:
        if k in in_dict:
            return in_dict[k]
    return None

def _deepcopy(x: Any) -> Any:
    import copy
    try:
        return copy.deepcopy(x)
    except Exception:
        # Fall back to a shallow copy if something odd is inside
        if isinstance(x, dict):
            return dict(x)
        if isinstance(x, list):
            return list(x)
        return x

def _deep_merge(base: Any, overlay: Any) -> Any:
    """Shallow-on-lists, deep-on-dicts merge; overlay wins."""
    if isinstance(base, dict) and isinstance(overlay, dict):
        out: Dict[str, Any] = {}
        for k in base.keys() | overlay.keys():
            if k in overlay:
                out[k] = _deep_merge(base.get(k), overlay[k])
            else:
                out[k] = _deepcopy(base[k])
        return out
    # For lists and primitives, overlay replaces
    return _deepcopy(overlay) if overlay is not None else _deepcopy(base)

def _walk_strings(node: Any, fn: Callable[[str], str], props: Optional[Iterable[str]] = None) -> Any:
    """Recursively apply fn to all strings (optionally only to certain property names)."""
    if isinstance(node, dict):
        out = {}
        for k, v in node.items():
            if props and k not in props:
                out[k] = _walk_strings(v, fn, props)
            else:
                out[k] = fn(v) if isinstance(v, str) else _walk_strings(v, fn, props)
        return out
    if isinstance(node, list):
        return [_walk_strings(v, fn, props) for v in node]
    return fn(node) if isinstance(node, str) else node

def _apply_single_mod(obj: Dict[str, Any], prop: str, spec: Dict[str, Any], warn: Callable[[str], None]) -> None:
    """Apply one mod spec to obj[prop]. Tolerant to minor schema variations."""
    mode = spec.get("mode")
    if not mode:
        warn(f"⚠️ Skipping _mod for key '{prop}' due to missing 'mode': {spec}")
        return

    # Text replacement across the whole object (or within certain props)
    if mode == "replaceTxt":
        repl = spec.get("replace")
        with_ = spec.get("with", "")
        props = spec.get("props")
        flags = spec.get("flags", "")
        if not isinstance(repl, str):
            warn(f"⚠️ Skipping replaceTxt for key '{prop}' due to non-string 'replace'")
            return
        pat = re.compile(repl, re.I if "i" in flags.lower() else 0)
        def _fn(s: str) -> str:
            return pat.sub(with_, s)
        new_obj = _walk_strings(obj if prop == "*" else obj.get(prop, {}), _fn, props)
        if prop == "*":
            obj.clear()
            obj.update(new_obj)
        else:
            obj[prop] = new_obj
        return

    # Root-level structure adjustments
    if prop == "_" and mode == "addSkills":
        skills = spec.get("skills", {})
        if isinstance(skills, dict):
            cur = obj.get("skill", {})
            if isinstance(cur, dict):
                cur.update(skills)
                obj["skill"] = cur
        return

    # Array operations against obj[prop]
    if prop not in obj or not isinstance(obj[prop], list):
        warn(f"⚠️ Skipping _mod for key '{prop}' because value is not an array: {type(obj.get(prop))}")
        return

    arr: List[Any] = obj[prop]
    items = _coalesce("items", "itemss", "iteems", in_dict=spec)
    if mode in {"appendArr", "prependArr", "insertArr", "replaceArr"} and items is None:
        warn(f"⚠️ Skipping _mod for key '{prop}' due to missing 'items' in {mode}")
        return

    # Normalize items to list
    if items is not None and not isinstance(items, list):
        items = [items]

    if mode == "appendArr":
        arr.extend(items)  # type: ignore[arg-type]
        return

    if mode == "prependArr":
        obj[prop] = list(items) + arr  # type: ignore[list-item]
        return

    if mode == "insertArr":
        idx = spec.get("index", 0)
        try:
            idx = int(idx)
        except Exception:
            idx = 0
        for i, itm in enumerate(items):  # type: ignore[assignment]
            arr.insert(idx + i, itm)
        return

    if mode == "replaceArr":
        target = spec.get("replace")
        if isinstance(target, dict) and "index" in target:
            try:
                idx = int(target["index"])
                for i, itm in enumerate(items):
                    if 0 <= idx + i < len(arr):
                        arr[idx + i] = itm
                    else:
                        arr.append(itm)
                return
            except Exception:
                pass
        # Name-based replacement
        def _name_of(x: Any) -> Optional[str]:
            return x.get("name") if isinstance(x, dict) else None
        if isinstance(target, str):
            replaced = False
            for i, el in enumerate(arr):
                if _name_of(el) == target:
                    # replace first match; if multiple items -> insert/extend suitably
                    arr[i:i+1] = items
                    replaced = True
                    break
            if not replaced:
                # If no match, append as a fallback
                arr.extend(items)
        return

    if mode == "removeArr":
        names = spec.get("names")
        if isinstance(names, str):
            names = [names]
        if isinstance(names, list):
            names_set = set(names)
            obj[prop] = [el for el in arr if not (isinstance(el, dict) and el.get("name") in names_set)]
        return

    if mode == "appendIfNotExistsArr":
        to_add = items or []
        cur = arr
        existing = set()
        for el in cur:
            if isinstance(el, str):
                existing.add(el)
            elif isinstance(el, dict) and "name" in el:
                existing.add(el["name"])
        for el in to_add:
            key = el if isinstance(el, str) else (el.get("name") if isinstance(el, dict) else None)
            if key and key not in existing:
                cur.append(el)
        return

    # Unknown mode: ignore with warning
    warn(f"⚠️ Unknown _mod mode '{mode}' for key '{prop}' — skipping.")

def _apply_mods(obj: Dict[str, Any], mods: Any, warn: Callable[[str], None]) -> None:
    """Apply a `_mod` block that may be a dict mapping prop->spec or list of specs."""
    if not mods:
        return
    if isinstance(mods, dict):
        for prop, spec in mods.items():
            if isinstance(spec, list):
                for s in spec:
                    if isinstance(s, dict):
                        _apply_single_mod(obj, prop, s, warn)
                    else:
                        warn(f"⚠️ Skipping _mod for key '{prop}' due to non-dict entry in list: {type(s)}")
            elif isinstance(spec, dict):
                _apply_single_mod(obj, prop, spec, warn)
            else:
                warn(f"⚠️ Skipping _mod for key '{prop}' because value is {type(spec)} not dict/list")
    elif isinstance(mods, list):
        # If it's a bare list, assume root-level prop "_" (convention we saw in prior data)
        for s in mods:
            if isinstance(s, dict):
                _apply_single_mod(obj, "_", s, warn)
            else:
                warn(f"⚠️ Skipping _mod entry due to non-dict type: {type(s)}")
    else:
        warn(f"⚠️ Skipping _mod due to unexpected type: {type(mods)}")

def resolve_copy(
    obj: Dict[str, Any],
    resolver: Optional[Union[Callable[[str, str], Optional[Dict[str, Any]]], Dict[Tuple[str, str], Dict[str, Any]]]] = None,
    *,
    filename: Optional[str] = None,
    warn: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """
    Resolve 5eTools-style `_copy`/`copy` with optional `_mod` patches.
    - `resolver` may be a callable (name, source) -> base dict, or a dict keyed by (name, source).
    - If no resolver is provided or base isn't found, returns obj cloned and still applies `_mod` against it.
    - Tolerant to slightly malformed `_mod` specs (prints warnings and skips).
    """
    _warn = warn or (lambda msg: print(msg))

    spec = obj.get("_copy") or obj.get("copy")
    base: Optional[Dict[str, Any]] = None

    if isinstance(spec, dict) and resolver is not None:
        name = spec.get("name")
        src = spec.get("source") or spec.get("src") or spec.get("from")
        if callable(resolver):
            try:
                base = resolver(name, src)  # type: ignore[misc]
            except Exception as e:
                _warn(f"⚠️ resolve_copy resolver failed for ({name}, {src}): {e}")
        elif isinstance(resolver, dict):
            base = resolver.get((name, src))

    # If there is no base, start from the object itself
    overlay = {k: v for k, v in obj.items() if k not in ("_copy", "copy", "_mod")}
    if base:
        merged = _deep_merge(base, overlay)
    else:
        merged = _deepcopy(overlay)

    # Apply _mod from the object-level (and support misplaced _mod inside spec as a fallback)
    mods = obj.get("_mod") or (spec.get("_mod") if isinstance(spec, dict) else None)
    _apply_mods(merged, mods, _warn)
    return merged

def stamp_doc_meta(
    doc: Dict[str, Any],
    collection: Optional[str] = None,
    *,
    source_path: Optional[Union[str, "Path"]] = None,
    source_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Ensure a `meta` dict exists and stamp standard provenance fields.
    Backwards compatible with the older single-argument signature.
    """
    if not isinstance(doc, dict):
        # keep shape predictable if a non-dict sneaks through
        wrapped = {"value": doc, "meta": {}}
        if collection:
            wrapped["meta"]["collection"] = collection
        if source_path:
            wrapped["meta"]["source_path"] = str(source_path)
        if source_id:
            wrapped["meta"]["source_id"] = source_id
        if extra:
            wrapped["meta"].update(extra)
        return wrapped

    meta = doc.setdefault("meta", {})
    if collection:
        meta["collection"] = collection
    if source_path:
        meta["source_path"] = str(source_path)
    if source_id:
        meta["source_id"] = source_id
    if "id" in doc and "id" not in meta:
        meta["id"] = doc["id"]
    if "source" in doc and "source" not in meta:
        meta["source"] = doc["source"]
    if extra:
        meta.update(extra)
    return doc

def _node_text(node: Any) -> Optional[str]:
    """Extract text from a node or NodeWithScore, if possible."""
    try:
        n = getattr(node, "node", node)
        if hasattr(n, "get_content") and callable(n.get_content):
            return n.get_content()
        if hasattr(n, "text"):
            return n.text
        if isinstance(n, dict):
            for k in ("text", "content", "body"):
                if k in n and isinstance(n[k], str):
                    return n[k]
        if isinstance(n, str):
            return n
        return str(n)
    except Exception:
        return None

def _node_meta(node: Any) -> Optional[dict]:
    """Extract metadata from a node or NodeWithScore, if possible."""
    try:
        n = getattr(node, "node", node)
        if hasattr(n, "metadata"):
            return getattr(n, "metadata")
        if isinstance(n, dict):
            return n.get("metadata") or n.get("meta")
        return None
    except Exception:
        return None

def maybe_stitch_monster_actions(
    preferred: Any,
    text: Any,
    meta: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Safe helper to optionally stitch monster action text.

    - `preferred` may be a NodeWithScore, dict-like, or None.
    - `text` is the top hit's text; if it's not a string we try to coerce from `preferred`.
    - Never raises: on error, returns the best available plain text.
    - If we detect "see source entry for full actions" we currently return the original text;
      true stitching would require the full hit list, which we don't have here.
    """
    try:
        # Prefer the provided text if it's already a string
        top_text = text if isinstance(text, str) else _node_text(preferred) or str(text)

        # Obtain metadata if not explicitly provided
        if meta is None:
            try:
                meta = _node_meta(preferred) or {}
            except Exception:
                meta = {}
        else:
            meta = dict(meta)

        # Simple marker check for elided actions (no-op if detected)
        if "see source entry for full actions" in top_text.lower():
            return top_text  # don't modify, as it may be intentional elision

        # Example stitching logic (replace with actual requirements)
        name = (meta.get("name") or "").strip()
        if name and name not in top_text:
            # If the name is not already in the text, prepend it
            stitched = f"{name}: {top_text}"
            return stitched

        return top_text  # fallback to original top_text if no stitching applied

    except Exception as e:
        print(f"⚠️ Error in maybe_stitch_monster_actions: {e}")
        return str(text)  # ensure we return a string even on error