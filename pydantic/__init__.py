"""Minimal stand-in for :mod:`pydantic` used in tests."""
from __future__ import annotations

from dataclasses import dataclass
import sys
import types
from enum import Enum
from typing import Any, Callable, Dict, Mapping, Tuple, Type, get_args, get_origin, get_type_hints


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
    default: Any = _MISSING,
    *,
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

    @classmethod
    def _collect_annotations(cls) -> Dict[str, Any]:
        annotations: Dict[str, Any] = {}
        for base in reversed(cls.__mro__):
            module = sys.modules.get(base.__module__)
            globalns = getattr(module, "__dict__", {}) if module else {}
            try:
                hints = get_type_hints(base, globalns=globalns, include_extras=True)
            except Exception:
                hints = getattr(base, "__annotations__", {})
            for key, value in hints.items():
                if key.startswith("__pydantic"):
                    continue
                if isinstance(value, str):
                    try:
                        value = eval(value, globalns)
                    except Exception:
                        pass
                annotations[key] = value
        return annotations

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        defaults: Dict[str, _FieldDefault | Any] = {}
        aliases: Dict[str, str] = {}
        # Start with defaults defined on parent classes so subclasses inherit
        # previously declared fields.
        for base in cls.__mro__[1:]:
            defaults.update(getattr(base, "__pydantic_defaults__", {}))
            aliases.update(getattr(base, "__pydantic_aliases__", {}))

        annotations = cls._collect_annotations()
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
        annotations = self.__class__._collect_annotations()
        defaults: Dict[str, _FieldDefault | Any] = {}
        aliases: Dict[str, str] = {}
        for base in self.__class__.__mro__:
            defaults.update(getattr(base, "__pydantic_defaults__", {}))
            aliases.update(getattr(base, "__pydantic_aliases__", {}))
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
            value = _coerce_type(value, annotations.get(name))
            setattr(self, name, value)
        for extra, value in data.items():
            setattr(self, extra, value)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in {"__pydantic_defaults__", "__pydantic_aliases__"}:
            super().__setattr__(name, value)
            return
        annotations = self.__class__._collect_annotations()
        if name in annotations:
            value = _coerce_type(value, annotations[name])
        super().__setattr__(name, value)

    def model_dump(self, **kwargs: Any) -> Dict[str, Any]:  # kwargs for compatibility
        data = {name: _convert(getattr(self, name)) for name in self.__class__._collect_annotations()}
        # include dynamically assigned attributes that are not declared fields
        for key, value in self.__dict__.items():
            if key in data or key.startswith("__pydantic") or key.startswith("_"):
                continue
            if key in {"__pydantic_defaults__", "__pydantic_aliases__"}:
                continue
            data[key] = _convert(value)
        return data

    def dict(self, **kwargs: Any) -> Dict[str, Any]:
        return self.model_dump(**kwargs)

    def model_dump_json(self, *args: Any, **kwargs: Any) -> str:
        import json

        return json.dumps(self.model_dump(), *args, **kwargs)

    def copy(self) -> "BaseModel":
        return self.__class__(**self.dict())

    def model_copy(self, *, update: Dict[str, Any] | None = None, deep: bool = False) -> "BaseModel":
        data = self.model_dump()
        if update:
            data.update(update)
        return self.__class__(**data)

    @classmethod
    def model_validate(cls, data: Any) -> "BaseModel":
        if isinstance(data, cls):
            return data
        if isinstance(data, BaseModel):
            return cls(**data.dict())
        if isinstance(data, Mapping):
            return cls(**dict(data))
        raise TypeError(f"Cannot validate data of type {type(data)!r}")

    @classmethod
    def model_rebuild(cls, *args: Any, **kwargs: Any) -> None:
        """Compatibility shim for Pydantic v2's ``model_rebuild`` method."""

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        fields = ", ".join(f"{k}={getattr(self, k)!r}" for k in self.__class__.__annotations__)
        return f"{self.__class__.__name__}({fields})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.model_dump() == other.model_dump()


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


def _coerce_type(value: Any, expected_type: Any) -> Any:
    if value is None:
        return None
    if expected_type is None or expected_type is Any:
        return value

    origin = get_origin(expected_type)
    if origin is not None:
        if origin in (list, tuple, set):
            if not isinstance(value, (list, tuple, set)):
                return value
            args = get_args(expected_type) or (Any,)
            subtype = args[0]
            iterable = list(value) if origin is list else (tuple(value) if origin is tuple else set(value))
            converted = [_coerce_type(item, subtype) for item in iterable]
            if origin is list:
                return converted
            if origin is tuple:
                return tuple(converted)
            return set(converted)
        if origin is dict:
            if not isinstance(value, Mapping):
                return value
            key_type, val_type = (get_args(expected_type) or (Any, Any))[:2]
            return {
                _coerce_type(k, key_type): _coerce_type(v, val_type)
                for k, v in value.items()
            }
        union_type = getattr(types, "UnionType", None)
        if union_type is not None and origin is union_type:  # pragma: no cover - py3.11+
            for arg in get_args(expected_type):
                try:
                    return _coerce_type(value, arg)
                except Exception:
                    continue
            return value
        if str(origin).endswith("Union"):
            for arg in get_args(expected_type):
                try:
                    return _coerce_type(value, arg)
                except Exception:
                    continue
            return value
        if str(origin).endswith("Annotated"):
            args = get_args(expected_type)
            if args:
                return _coerce_type(value, args[0])
            return value

    if isinstance(expected_type, type):
        if issubclass(expected_type, BaseModel):
            if isinstance(value, expected_type):
                return value
            if isinstance(value, BaseModel):
                return expected_type.model_validate(value)
            if isinstance(value, Mapping):
                return expected_type(**dict(value))
        if issubclass(expected_type, Enum):
            return expected_type(value)
        try:
            return expected_type(value)
        except Exception:
            return value
    return value


class ConfigDict(dict):
    """Lightweight stand-in for :class:`pydantic.ConfigDict`.

    The real type is a ``TypedDict`` describing configuration options.  Tests
    only require that the name exists and behaves like a mapping, so a simple
    ``dict`` subclass is sufficient here.
    """


class PrivateAttr:
    """Descriptor used to declare private attributes on :class:`BaseModel`.

    The implementation here is intentionally small – it simply stores the
    value on the instance ``__dict__`` the first time it is accessed, falling
    back to the provided default or default factory when necessary.
    """

    def __init__(self, default: Any = _MISSING, default_factory: Callable[[], Any] | None = None):
        self.default = default
        self.default_factory = default_factory
        self.name: str | None = None

    def __set_name__(self, owner: type, name: str) -> None:  # pragma: no cover - simple assignment
        self.name = name

    def _initial_value(self) -> Any:
        if self.default_factory is not None:
            return self.default_factory()
        if self.default is not _MISSING:
            return self.default
        return None

    def __get__(self, instance: Any, owner: type | None = None) -> Any:
        if instance is None:
            return self
        assert self.name is not None  # nosec - set in __set_name__
        if self.name not in instance.__dict__:
            instance.__dict__[self.name] = self._initial_value()
        return instance.__dict__[self.name]

    def __set__(self, instance: Any, value: Any) -> None:
        assert self.name is not None  # nosec - set in __set_name__
        instance.__dict__[self.name] = value


class BaseSettings(BaseModel):
    """Drop-in replacement for :class:`pydantic.BaseSettings` used by tests."""


class AnyUrl(str):
    """Simplified placeholder for :class:`pydantic.AnyUrl`."""


class FilePath(str):
    """Simplified placeholder for :class:`pydantic.FilePath`."""


def BeforeValidator(func: Callable[..., Any]) -> Callable[..., Any]:
    """Return the validator function unchanged.

    The project only needs the decorator to exist so that user-defined
    validators can be declared.  Validation itself is handled elsewhere in the
    tests.
    """

    return func


class GetCoreSchemaHandler:
    def __call__(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        return {}


class GetJsonSchemaHandler:
    def __call__(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        return {}


class SerializationInfo:
    pass


class SerializerFunctionWrapHandler:
    def __call__(self, value: Any, handler: Callable[..., Any] | None = None) -> Any:
        if handler is not None:
            return handler(value)
        return value


class ValidationInfo:
    pass


class JsonSchemaValue(dict):
    pass


class FieldInfo:
    def __init__(self, default: Any = None, **kwargs: Any) -> None:
        self.default = default
        self.extra = kwargs


class Secret:
    def __init__(self, value: Any) -> None:
        self._value = value

    def get_secret_value(self) -> Any:
        return self._value

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return "Secret(******)"


class SecretStr(Secret, str):
    def __new__(cls, value: str) -> "SecretStr":
        obj = str.__new__(cls, value)
        Secret.__init__(obj, value)
        return obj


class SerializeAsAny:
    def __class_getitem__(cls, item: Any) -> type:
        return cls


class WithJsonSchema:
    def __init__(self, schema: Dict[str, Any], mode: str | None = None) -> None:
        self.schema = schema
        self.mode = mode


StrictInt = int
StrictFloat = float
StrictStr = str


def PlainSerializer(*args: Any, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        return func

    return decorator


def WrapSerializer(*args: Any, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        return func

    return decorator


def field_validator(*args: Any, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        return func

    return decorator


def validator(*args: Any, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    return field_validator(*args, **kwargs)


def model_validator(*args: Any, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        return func

    return decorator


def field_serializer(*args: Any, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        return func

    return decorator


def model_serializer(*args: Any, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        return func

    return decorator


def create_model(name: str, **fields: Tuple[type, Any]) -> Type[BaseModel]:
    annotations: Dict[str, type] = {}
    namespace: Dict[str, Any] = {}
    for field_name, value in fields.items():
        if isinstance(value, tuple):
            if len(value) == 2:
                field_type, default = value
            elif len(value) > 2:
                field_type, default = value[0], value[1]
            else:
                field_type, default = value[0], _MISSING
        else:
            field_type, default = Any, value
        annotations[field_name] = field_type if isinstance(field_type, type) else Any
        if default is not _MISSING:
            namespace[field_name] = default
    namespace["__annotations__"] = annotations
    return type(name, (BaseModel,), namespace)


class TypeAdapter:
    def __init__(self, typ: type) -> None:
        self.typ = typ

    def validate_python(self, value: Any) -> Any:
        return value


__all__ = [
    "BaseModel",
    "BaseSettings",
    "Field",
    "ConfigDict",
    "PrivateAttr",
    "AnyUrl",
    "FilePath",
    "BeforeValidator",
    "GetCoreSchemaHandler",
    "GetJsonSchemaHandler",
    "PlainSerializer",
    "PrivateAttr",
    "Secret",
    "SecretStr",
    "SerializationInfo",
    "SerializeAsAny",
    "SerializerFunctionWrapHandler",
    "StrictFloat",
    "StrictInt",
    "StrictStr",
    "TypeAdapter",
    "ValidationError",
    "ValidationInfo",
    "WithJsonSchema",
    "WrapSerializer",
    "create_model",
    "field_serializer",
    "field_validator",
    "model_serializer",
    "model_validator",
    "FieldInfo",
    "JsonSchemaValue",
    "validator",
]


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
