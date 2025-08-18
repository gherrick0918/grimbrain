from __future__ import annotations

from typing import List


def canonicalize_id(doc_type: str, raw_id: str) -> str:
    """Return canonical form of *raw_id* for *doc_type*.

    - lowercases the id
    - removes leading "<doc_type>." if present
    - for spells, replaces underscores with dots
    """
    cid = (raw_id or "").strip().lower()
    prefix = f"{doc_type}."
    if cid.startswith(prefix):
        cid = cid[len(prefix):]
    if doc_type == "spell":
        cid = cid.replace("_", ".")
    return cid
