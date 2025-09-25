"""Minimal stub of jsonschema for offline testing."""
from __future__ import annotations

from typing import Any, Iterable


class ValidationError(Exception):
    pass


class _Error:
    def __init__(self, path: list[str], message: str) -> None:
        self.path = path
        self.message = message


class Draft202012Validator:
    """Extremely small subset of the jsonschema validator."""

    def __init__(self, schema: Any) -> None:
        self.schema = schema

    def iter_errors(self, instance: Any) -> Iterable[_Error]:
        yield from _validate(instance, self.schema, path=[])


def _validate(instance: Any, schema: Any, path: list[str]) -> Iterable[_Error]:
    if not isinstance(schema, dict):
        return []

    errors: list[_Error] = []

    required = schema.get("required")
    if isinstance(required, list) and isinstance(instance, dict):
        for key in required:
            if key not in instance:
                errors.append(_Error(path + [key], f"'{key}' is a required property"))

    schema_type = schema.get("type")
    if schema_type == "object" and isinstance(instance, dict):
        props = schema.get("properties", {})
        for key, subschema in props.items():
            if key in instance:
                errors.extend(_validate(instance[key], subschema, path + [key]))
    elif schema_type == "integer":
        if not isinstance(instance, int):
            errors.append(_Error(path, "Expected integer"))
        else:
            minimum = schema.get("minimum")
            maximum = schema.get("maximum")
            if minimum is not None and instance < minimum:
                errors.append(_Error(path, f"Value {instance} is less than minimum {minimum}"))
            if maximum is not None and instance > maximum:
                errors.append(_Error(path, f"Value {instance} is greater than maximum {maximum}"))
    elif schema_type == "array" and isinstance(instance, list):
        item_schema = schema.get("items")
        if item_schema:
            for idx, item in enumerate(instance):
                errors.extend(_validate(item, item_schema, path + [str(idx)]))

    return errors


__all__ = ["Draft202012Validator", "ValidationError"]
