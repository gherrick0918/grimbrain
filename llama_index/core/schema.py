"""Small subset of ``llama_index.core.schema`` for tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


def _generate_id() -> str:
    import uuid

    return str(uuid.uuid4())


@dataclass
class Document:
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    doc_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.doc_id is None:
            self.doc_id = _generate_id()


@dataclass
class TextNode:
    text: str
    metadata: Dict[str, Any]
    node_id: str

    def get_content(self) -> str:
        return self.text


__all__ = ["Document", "TextNode"]
