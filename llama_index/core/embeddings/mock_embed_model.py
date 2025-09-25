"""Deterministic mock embedding used by tests."""

from __future__ import annotations

from typing import Iterable, List


class MockEmbedding:
    """A tiny, deterministic embedding model suitable for unit tests."""

    def __init__(self, embed_dim: int = 8) -> None:
        self.embed_dim = embed_dim

    def _encode(self, text: str) -> List[float]:
        # Produce a deterministic pseudo-embedding by hashing characters.
        values = [0.0] * self.embed_dim
        if not text:
            return values
        for idx, ch in enumerate(text):
            values[idx % self.embed_dim] += (ord(ch) % 31) / 30.0
        return values

    def get_text_embedding(self, text: str) -> List[float]:
        return self._encode(text)

    def get_text_embedding_batch(self, texts: Iterable[str]) -> List[List[float]]:
        return [self.get_text_embedding(t) for t in texts]

    def get_query_embedding(self, text: str) -> List[float]:
        return self.get_text_embedding(text)


__all__ = ["MockEmbedding"]
