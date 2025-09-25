"""Chroma vector store shim used in tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional


@dataclass
class _StoredNode:
    id: str
    text: str
    metadata: dict


class ChromaVectorStore:
    """Thin wrapper around a Chroma collection.

    We only use a handful of methods from the real implementation.  The shim
    stores/retrieves simple payloads and leaves persistence to the underlying
    collection.
    """

    def __init__(self, collection) -> None:
        self.collection = collection

    @classmethod
    def from_collection(cls, collection) -> "ChromaVectorStore":
        return cls(collection)

    def add_nodes(self, nodes: Iterable, *, embed_model=None) -> None:
        ids: List[str] = []
        texts: List[str] = []
        metadatas: List[dict] = []
        embeddings: Optional[List[List[float]]] = None

        if embed_model is not None:
            embeddings = []

        for node in nodes:
            node_id = getattr(node, "node_id", None) or getattr(node, "id", None)
            if node_id is None:
                raise ValueError("Node is missing an identifier")
            ids.append(str(node_id))
            text = getattr(node, "text", "")
            texts.append(text)
            meta = dict(getattr(node, "metadata", {}) or {})
            metadatas.append(meta)
            if embeddings is not None:
                embeddings.append(embed_model.get_text_embedding(text))

        kwargs = {"ids": ids, "metadatas": metadatas, "documents": texts}
        if embeddings is not None:
            kwargs["embeddings"] = embeddings
        if hasattr(self.collection, "upsert"):
            self.collection.upsert(**kwargs)
        else:
            self.collection.add(**kwargs)

    def query(self, query: str, *, top_k: int = 10, embed_model=None) -> List[dict]:
        if hasattr(self.collection, "query"):
            query_kwargs = {"n_results": top_k}
            if embed_model is not None and hasattr(embed_model, "get_query_embedding"):
                query_kwargs["query_embeddings"] = [embed_model.get_query_embedding(query)]
            else:
                query_kwargs["query_texts"] = [query]
            raw = self.collection.query(**query_kwargs)
            ids = raw.get("ids", [[]])[0]
            docs = raw.get("documents", [[]])[0]
            metas = raw.get("metadatas", [[]])[0]
            scores = raw.get("distances", [[]])[0]
        else:
            raise RuntimeError("Underlying collection does not support querying")

        results: List[dict] = []
        for idx, doc_id in enumerate(ids):
            results.append(
                {
                    "id": doc_id,
                    "text": docs[idx] if idx < len(docs) else "",
                    "metadata": metas[idx] if idx < len(metas) else {},
                    "score": scores[idx] if idx < len(scores) else 0.0,
                }
            )
        return results

    def persist(self) -> None:
        if hasattr(self.collection, "persist"):
            self.collection.persist()


__all__ = ["ChromaVectorStore"]
