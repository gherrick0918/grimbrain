"""Minimal stub of jsonschema for offline testing."""
from __future__ import annotations

from typing import Any, Iterable


class ValidationError(Exception):
    pass


class Draft202012Validator:
    def __init__(self, schema: Any) -> None:
        self.schema = schema

    def iter_errors(self, instance: Any) -> Iterable[Any]:
        return []


__all__ = ["Draft202012Validator", "ValidationError"]
