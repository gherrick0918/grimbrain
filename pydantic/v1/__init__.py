"""Minimal compatibility shim for :mod:`pydantic.v1`."""
from __future__ import annotations

from .. import (
    AnyUrl,
    BaseModel,
    BaseSettings,
    ConfigDict,
    Field,
    ValidationError,
    field_serializer,
    field_validator,
    model_serializer,
    model_validator,
    validator,
)

__all__ = [
    "AnyUrl",
    "BaseModel",
    "BaseSettings",
    "ConfigDict",
    "Field",
    "ValidationError",
    "field_serializer",
    "field_validator",
    "model_serializer",
    "model_validator",
    "validator",
]
