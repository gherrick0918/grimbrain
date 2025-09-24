"""Minimal stand-in for :mod:`pydantic` used in tests."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping


class _Missing:
    pass


_MISSING = _Missing()


@dataclass
class _FieldDefault:
    default: Any = _MISSING
    factory: Callable[[], Any] | None = None
    alias: str | None = None
    metadata: Dict[str, Any] | None = None

    def get(self) -> Any:
        if self.factory is not None:
            return self.factory()
        return self.default


def Field(
    *,
    default: Any = _MISSING,
    default_factory: Callable[[], Any] | None = None,
    alias: str | None = None,
    **kwargs: Any,
) -> _FieldDefault:
    metadata: Dict[str, Any] | None = None
    if kwargs:
        metadata = dict(kwargs)
    return _FieldDefault(default=default, factory=default_factory, alias=alias, metadata=metadata)


class BaseModel:
    __pydantic_defaults__: Dict[str, _FieldDefault | Any] = {}
    __pydantic_aliases__: Dict[str, str] = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        defaults: Dict[str, _FieldDefault | Any] = {}
        annotations = getattr(cls, "__annotations__", {})
        aliases: Dict[str, str] = {}
        for name in annotations:
            value = getattr(cls, name, _MISSING)
            if isinstance(value, _FieldDefault):
                defaults[name] = value
                if value.alias:
                    aliases[value.alias] = name
            elif value is not _MISSING:
                defaults[name] = value
        cls.__pydantic_defaults__ = defaults
        cls.__pydantic_aliases__ = aliases

    def __init__(self, **data: Any) -> None:
        annotations = getattr(self.__class__, "__annotations__", {})
        defaults = getattr(self.__class__, "__pydantic_defaults__", {})
        aliases = getattr(self.__class__, "__pydantic_aliases__", {})
        for alias, field_name in aliases.items():
            if alias in data and field_name not in data:
                data[field_name] = data.pop(alias)
        for name in annotations:
            if name in data:
                value = data.pop(name)
            elif name in defaults:
                default_value = defaults[name]
                if isinstance(default_value, _FieldDefault):
                    value = default_value.get()
                else:
                    value = default_value
                    if isinstance(value, (list, dict, set)):
                        value = value.copy()
            else:
                value = None
            setattr(self, name, value)
        for extra, value in data.items():
            setattr(self, extra, value)

    def dict(self) -> Dict[str, Any]:
        return {name: _convert(getattr(self, name)) for name in self.__class__.__annotations__}

    def model_dump(self) -> Dict[str, Any]:
        return self.dict()

    def copy(self) -> "BaseModel":
        return self.__class__(**self.dict())

    @classmethod
    def model_validate(cls, data: Any) -> "BaseModel":
        if isinstance(data, cls):
            return data
        if isinstance(data, BaseModel):
            return cls(**data.dict())
        if isinstance(data, Mapping):
            return cls(**dict(data))
        raise TypeError(f"Cannot validate data of type {type(data)!r}")

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        fields = ", ".join(f"{k}={getattr(self, k)!r}" for k in self.__class__.__annotations__)
        return f"{self.__class__.__name__}({fields})"


def _convert(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.dict()
    if isinstance(value, list):
        return [_convert(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_convert(v) for v in value)
    if isinstance(value, Mapping):
        return {k: _convert(v) for k, v in value.items()}
    return value


__all__ = ["BaseModel", "Field"]


class ValidationError(Exception):
    def __init__(self, errors: Any | None = None) -> None:
        super().__init__("validation error")
        if errors is None:
            errors = []
        self._errors = errors

    def errors(self, include_url: bool = True) -> Any:
        return self._errors


class PositiveInt(int):
    pass


__all__.extend(["PositiveInt", "ValidationError"])
