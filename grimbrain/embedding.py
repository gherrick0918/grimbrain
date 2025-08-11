from sentence_transformers import SentenceTransformer
from pydantic import Field
from typing import Any

try:
    from llama_index.core.embeddings import BaseEmbedding
except ImportError:  # pragma: no cover - fallback for older versions
    from llama_index.embeddings import BaseEmbedding


class CustomLocalEmbedding(BaseEmbedding):
    model: Any = Field(..., exclude=True)

    def __init__(self, model_name: str):
        super().__init__(model=SentenceTransformer(model_name))

    def _get_text_embedding(self, text: str) -> list[float]:
        return self.model.encode(text).tolist()

    def _get_query_embedding(self, query: str) -> list[float]:
        return self.model.encode(query).tolist()

    async def _aget_query_embedding(self, query: str) -> list[float]:
        return self._get_query_embedding(query)

    def get_text_embedding_batch(self, texts, show_progress=True):
        return self.model.encode(texts, show_progress_bar=show_progress).tolist()

    def embed_query(self, query: str) -> list[float]:
        return self._get_query_embedding(query)
