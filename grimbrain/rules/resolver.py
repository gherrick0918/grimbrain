from __future__ import annotations

import os
import sys
import time
import difflib
from pathlib import Path
from typing import Dict, Tuple, List, Optional, Set
from collections import OrderedDict

try:  # pragma: no cover - optional dependency
    from chromadb import PersistentClient
except Exception:  # pragma: no cover
    PersistentClient = None  # type: ignore

from .index import load_rules


class RuleResolver:
    """Resolve a user verb to a rule document.

    The resolver first attempts exact matches against ids, cli verbs and aliases.
    Failing that it performs a very small vector similarity search using the
    pre-built Chroma index.  As a final fallback a difflib fuzzy match is used so
    tests can run without the Chroma dependency.
    """

    def __init__(
        self, rules_dir: str | Path | None = None, chroma_dir: str | Path | None = None
    ):
        self.rules_dir = Path(rules_dir or os.getenv("GB_RULES_DIR", "rules"))
        self.chroma_dir = Path(chroma_dir or os.getenv("GB_CHROMA_DIR", ".chroma"))
        self._cache: OrderedDict[
            Tuple[str, Optional[str], Optional[str]], Optional[dict]
        ] = OrderedDict()
        self._cache_size = 512
        self._load_config()
        self._load_rules()
        self._init_collection()

    # configuration ----------------------------------------------------
    def _env_int(self, name: str, default: int) -> int:
        try:
            return int(os.getenv(name, default))
        except Exception:
            return default

    def _env_float(self, name: str, default: float) -> float:
        try:
            return float(os.getenv(name, default))
        except Exception:
            return default

    def _load_config(self) -> None:
        self.k = self._env_int("GB_RESOLVER_K", 5)
        self.min_score_default = self._env_float("GB_RESOLVER_MIN_SCORE", 0.45)
        self.min_score_kind: Dict[str, float] = {}
        for kind in ["rule", "spell", "monster"]:
            val = os.getenv(f"GB_RESOLVER_MIN_SCORE_{kind.upper()}")
            if val is not None:
                try:
                    self.min_score_kind[kind] = float(val)
                except Exception:
                    pass
        self.warm_count = self._env_int("GB_RESOLVER_WARM_COUNT", 200)
        dbg = os.getenv("GB_RESOLVER_DEBUG") or os.getenv("GB_DEBUG")
        self.debug = str(dbg).lower() in {"1", "true", "yes"}

    def _init_collection(self) -> None:
        self.collection = None
        if PersistentClient is None:
            return
        try:
            client = PersistentClient(path=str(self.chroma_dir))
            self.collection = client.get_collection("content")
        except Exception:
            self.collection = None

    def _load_rules(self) -> None:
        self.rules: Dict[str, dict] = {}
        self.name_map: Dict[str, str] = {}
        self.verb_map: Dict[str, str] = {}
        rule_list, _, _, _ = load_rules(self.rules_dir)
        for rule in rule_list:
            rid = rule["id"]
            self.rules[rid] = rule
            self.name_map[rid.lower()] = rid
            verb = rule.get("cli_verb")
            if verb:
                self.name_map[verb.lower()] = rid
                self.verb_map[verb.lower()] = verb
            for alias in rule.get("aliases", []):
                self.name_map[alias.lower()] = rid
                if verb:
                    self.verb_map[alias.lower()] = verb

    # cache management -------------------------------------------------
    def _cache_put(self, key, value):
        self._cache[key] = value
        self._cache.move_to_end(key)
        if len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)

    def reload(self) -> None:
        self._cache.clear()
        self.verb_map.clear()
        self._load_rules()
        self._init_collection()
        # reload uses same config

    def warm(self) -> str:
        if self.collection is None:
            return "Warmed resolver cache for 0 docs in 0.00s."
        start = time.time()
        docs: List[str] = []
        try:
            total = self.collection.count()
            n = min(total, self.warm_count)
            res = self.collection.get(limit=n, include=["documents"])
            docs = res.get("documents", [])
            batch = 32
            for i in range(0, len(docs), batch):
                chunk = docs[i : i + batch]
                try:
                    self.collection.query(query_texts=chunk, n_results=1)
                except Exception:
                    break
        except Exception:
            docs = []
        dur = time.time() - start
        return f"Warmed resolver cache for {len(docs)} docs in {dur:.2f}s."

    # public API -------------------------------------------------------
    def resolve(
        self, text: str, kind: str | None = None, subkind: str | None = None
    ) -> Tuple[Optional[dict], List[Tuple[str, float]]]:
        key = (text.lower(), kind, subkind)
        if key in self._cache:
            result = self._cache[key]
            if result is None:
                return None, []
            return result, []

        # exact match --------------------------------------------------
        rid = self.name_map.get(text.lower())
        if rid:
            rule = self.rules[rid]
            self._cache_put(key, rule)
            return rule, []

        min_score = self.min_score_kind.get(kind or "", self.min_score_default)

        # vector search ------------------------------------------------
        vec_matches = self._vector_lookup(text, kind, subkind, min_score)
        if self.debug:
            dbg = [(r, round(s, 2), p) for r, s, p in vec_matches]
            print(
                f"[resolver] query=\"{text}\" kind={kind} k={self.k} -> matches={dbg}",
                file=sys.stderr,
            )

        suggestions: List[Tuple[str, float]] = []
        rule: Optional[dict] = None
        if vec_matches:
            top_id, top_score, _ = vec_matches[0]
            candidate = self.rules.get(top_id)
            if candidate is not None:
                q_tokens = set(text.lower().split())
                doc_tokens = {top_id.lower()}
                doc_tokens.update(candidate.get("cli_verb", "").lower().split())
                doc_tokens.update(a.lower() for a in candidate.get("aliases", []))
                if not q_tokens.isdisjoint(doc_tokens):
                    rule = candidate
                    vec_matches = vec_matches[1:]
        # fuzzy suggestions -------------------------------------------
        fuzzy = self._fuzzy_lookup(text, kind, subkind, min_score)

        merged: Dict[str, Tuple[float, Optional[str]]] = {}
        for rid2, score2, pack in vec_matches:
            merged[rid2] = (score2, pack)
        for rid2, score2 in fuzzy:
            if rid2 in merged:
                if score2 > merged[rid2][0]:
                    merged[rid2] = (score2, merged[rid2][1])
            else:
                merged[rid2] = (score2, None)
        suggestions = [(rid2, sc) for rid2, (sc, _) in merged.items()]
        suggestions.sort(key=lambda x: x[1], reverse=True)
        suggestions = suggestions[:5]

        if len(suggestions) < 5 and min_score < 0.99:
            existing = {rid for rid, _ in suggestions}
            for s in self.suggest_verbs(text):
                if s not in existing:
                    suggestions.append((s, 0.0))
                if len(suggestions) >= 5:
                    break

        self._cache_put(key, rule)
        return rule, suggestions

    # verb suggestions -------------------------------------------------
    def suggest_verbs(self, verb: str) -> List[str]:
        query = verb.lower()
        scored: List[Tuple[int, int, float, str]] = []
        for alias, canon in self.verb_map.items():
            start = 1 if alias.startswith(query) else 0
            sub = 1 if query in alias else 0
            ratio = difflib.SequenceMatcher(None, query, alias).ratio()
            scored.append((start, sub, ratio, canon))
        scored.sort(key=lambda x: (-x[0], -x[1], -x[2], x[3]))
        suggestions: List[str] = []
        seen: Set[str] = set()
        for _, _, _, canon in scored:
            if canon not in seen:
                seen.add(canon)
                suggestions.append(canon)
            if len(suggestions) >= 10:
                break
        return suggestions

    # helpers ----------------------------------------------------------
    def _vector_lookup(
        self, text: str, kind: str | None, subkind: str | None, min_score: float
    ) -> List[Tuple[str, float, Optional[str]]]:
        matches: List[Tuple[str, float, Optional[str]]] = []
        if self.collection is not None:
            where = {"doc_type": "rule"}
            try:
                res = self.collection.query(
                    query_texts=[text], n_results=self.k, where=where
                )
                ids = res.get("ids", [[]])[0]
                dists = res.get("distances", [[]])[0]
                metas = res.get("metadatas", [[]])[0]
                for rid, dist, meta in zip(ids, dists, metas):
                    if kind and meta.get("kind") != kind:
                        continue
                    if subkind and meta.get("subkind") != subkind:
                        continue
                    score = 1.0 - float(dist)
                    if score >= min_score:
                        matches.append((rid, score, meta.get("pack")))
            except Exception:
                pass
        return matches

    def _fuzzy_lookup(
        self, text: str, kind: str | None, subkind: str | None, min_score: float
    ) -> List[Tuple[str, float]]:
        scored: List[Tuple[str, float]] = []
        for name, rid in self.name_map.items():
            rule = self.rules[rid]
            if kind and rule.get("kind") != kind:
                continue
            if subkind and rule.get("subkind") != subkind:
                continue
            s = difflib.SequenceMatcher(a=text.lower(), b=name).ratio()
            if s >= min_score:
                scored.append((rid, s))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[: self.k]
