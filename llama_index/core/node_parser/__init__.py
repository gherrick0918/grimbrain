"""Simple node parser shim used for Grimbrain tests."""

from __future__ import annotations

from typing import Iterable, List

from ..schema import Document, TextNode


class SimpleNodeParser:
    """Convert documents into single TextNode instances.

    The real LlamaIndex implementation handles sophisticated chunking.  Our
    documents are already concise, so the shim simply wraps each document in a
    ``TextNode`` preserving metadata and identifiers.
    """

    def get_nodes_from_documents(self, documents: Iterable[Document]) -> List[TextNode]:
        nodes: List[TextNode] = []
        for doc in documents:
            nodes.append(TextNode(text=doc.text, metadata=dict(doc.metadata), node_id=doc.doc_id))
        return nodes


__all__ = ["SimpleNodeParser"]
