from __future__ import annotations

import os
import difflib
from pathlib import Path
from typing import Dict, Tuple, List, Optional
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
        self._load_rules()
        self._init_collection()

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
        rule_list, _, _, _ = load_rules(self.rules_dir)
        for rule in rule_list:
            rid = rule["id"]
            self.rules[rid] = rule
            self.name_map[rid.lower()] = rid
            verb = rule.get("cli_verb")
            if verb:
                self.name_map[verb.lower()] = rid
            for alias in rule.get("aliases", []):
                self.name_map[alias.lower()] = rid

    # cache management -------------------------------------------------
    def _cache_put(self, key, value):
        self._cache[key] = value
        self._cache.move_to_end(key)
        if len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)

    def reload(self) -> None:
        self._cache.clear()
        self._load_rules()
        self._init_collection()

    # public API -------------------------------------------------------
    def resolve(
        self, text: str, kind: str | None = None, subkind: str | None = None
    ) -> Tuple[Optional[dict], List[str]]:
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

        # vector search ------------------------------------------------
        rid, score = self._vector_lookup(text, kind, subkind)
        suggestions: List[str] = []
        rule: Optional[dict] = None
        if rid and score >= 0.42:
            candidate = self.rules.get(rid)
            if candidate is not None:
                q_tokens = set(text.lower().split())
                doc_tokens = {rid.lower()}
                doc_tokens.update(candidate.get("cli_verb", "").lower().split())
                doc_tokens.update(a.lower() for a in candidate.get("aliases", []))
                if not q_tokens.isdisjoint(doc_tokens):
                    rule = candidate
        elif rid and 0.30 <= score < 0.42:
            suggestions = [self.rules[rid]["id"]]
        self._cache_put(key, rule)
        return rule, suggestions

    # helpers ----------------------------------------------------------
    def _vector_lookup(
        self, text: str, kind: str | None, subkind: str | None
    ) -> Tuple[Optional[str], float]:
        if self.collection is not None:
            where = {"doc_type": "rule"}
            if kind:
                where["kind"] = kind
            if subkind:
                where["subkind"] = subkind
            try:
                res = self.collection.query(
                    query_texts=[text], n_results=1, where=where
                )
                ids = res.get("ids", [[]])[0]
                dists = res.get("distances", [[]])[0]
                if ids:
                    score = 1.0 - float(dists[0])
                    return ids[0], score
            except Exception:
                pass
        # fallback difflib --------------------------------------------
        best_id = None
        best_score = 0.0
        for name, rid in self.name_map.items():
            rule = self.rules[rid]
            if kind and rule.get("kind") != kind:
                continue
            if subkind and rule.get("subkind") != subkind:
                continue
            s = difflib.SequenceMatcher(a=text.lower(), b=name).ratio()
            if s > best_score:
                best_score = s
                best_id = rid
        return best_id, best_score
