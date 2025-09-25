"""Minimal llama_index.core shim used in the Grimbrain test suite."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional

from ..vector_stores.chroma import ChromaVectorStore


class _Settings:
    """Drop-in replacement for ``llama_index.core.Settings``.

    The real library exposes a module-level object with mutable attributes
    used to share global configuration (embedders, LLMs, etc.).  Tests set
    ``Settings.embed_model`` and ``Settings.llm`` directly, so we mirror that
    behaviour with a simple container object.
    """

    def __init__(self) -> None:
        self.embed_model = None
        self.llm = None


Settings = _Settings()


class StorageContext:
    """Very small wrapper that just holds onto a vector store instance."""

    def __init__(self, vector_store: ChromaVectorStore) -> None:
        self.vector_store = vector_store

    @classmethod
    def from_defaults(cls, *, vector_store: ChromaVectorStore) -> "StorageContext":
        return cls(vector_store)

    def persist(self) -> None:
        """Persist the underlying store if it exposes a ``persist`` method."""

        if hasattr(self.vector_store, "persist"):
            self.vector_store.persist()


@dataclass
class _Node:
    """Internal representation of a node stored in Chroma."""

    id: str
    text: str
    metadata: dict

    def get_content(self) -> str:
        return self.text


class NodeWithScore:
    """Simple score wrapper to mimic llama_index results."""

    def __init__(self, node: _Node, score: float) -> None:
        self.node = node
        self.score = score


class QueryEngine:
    """Very small query interface backed by Chroma collections."""

    def __init__(self, vector_store: ChromaVectorStore, *, embed_model=None, top_k: int = 10) -> None:
        self._store = vector_store
        self._embed_model = embed_model
        self._top_k = top_k

    def retrieve(self, query: str) -> List[NodeWithScore]:
        results = self._store.query(query, top_k=self._top_k, embed_model=self._embed_model)
        nodes: List[NodeWithScore] = []
        for row in results:
            node = _Node(id=row["id"], text=row["text"], metadata=row.get("metadata", {}) or {})
            nodes.append(NodeWithScore(node, score=row.get("score", 0.0)))
        return nodes


class VectorStoreIndex:
    """Extremely small subset used for writing/reading to Chroma."""

    def __init__(self, nodes: Iterable[_Node], *, storage_context: StorageContext, embed_model=None) -> None:
        self.storage_context = storage_context
        self.embed_model = embed_model
        if nodes:
            storage_context.vector_store.add_nodes(nodes, embed_model=embed_model)

    @classmethod
    def from_vector_store(
        cls, vector_store: ChromaVectorStore, *, embed_model=None
    ) -> "VectorStoreIndex":
        storage_context = StorageContext(vector_store=vector_store)
        index = cls([], storage_context=storage_context, embed_model=embed_model)
        return index

    def as_query_engine(self, similarity_top_k: int = 10) -> QueryEngine:
        return QueryEngine(self.storage_context.vector_store, embed_model=self.embed_model, top_k=similarity_top_k)


__all__ = [
    "Settings",
    "StorageContext",
    "VectorStoreIndex",
    "QueryEngine",
    "NodeWithScore",
]
