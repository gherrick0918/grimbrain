"""Minimal subset of Typer for offline testing."""
from __future__ import annotations

from typing import Any, Callable

from .models import ArgumentInfo, OptionInfo


class BadParameter(Exception):
    pass


class Exit(SystemExit):
    pass


class _Colors:
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


colors = _Colors()


class Context:
    def __init__(self, obj: Any | None = None) -> None:
        self.obj = obj


class Typer:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.commands: dict[str, Callable[..., Any]] = {}

    def command(self, *param_decls: str, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.commands[func.__name__] = func
            return func

        return decorator

    def callback(self, *param_decls: str, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self.command(*param_decls, **kwargs)

    def add_typer(self, app: "Typer", name: str | None = None) -> None:
        label = name or getattr(app, "name", f"typer_{len(self.commands)}")
        self.commands[label] = app

    def __call__(self, *args: Any, **kwargs: Any) -> None:  # pragma: no cover - CLI noop
        # No-op stub: real Typer would dispatch CLI commands.
        return None


def echo(message: Any, *, err: bool = False) -> None:
    print(message)


def secho(message: Any, *, fg: str | None = None) -> None:
    print(message)


def prompt(text: str, *, default: Any | None = None) -> Any:
    if default is not None:
        return default
    raise RuntimeError("typer.prompt called without default in stub environment")


def confirm(text: str, *, default: bool = False) -> bool:
    return default


def Option(default: Any = None, *param_decls: str, **kwargs: Any) -> OptionInfo:
    return OptionInfo(default=default, param_decls=param_decls, metadata=kwargs)


def Argument(default: Any = None, *param_decls: str, **kwargs: Any) -> ArgumentInfo:
    return ArgumentInfo(default=default, param_decls=param_decls, metadata=kwargs)


__all__ = [
    "Argument",
    "ArgumentInfo",
    "BadParameter",
    "Context",
    "Exit",
    "Option",
    "OptionInfo",
    "Typer",
    "colors",
    "confirm",
    "echo",
    "prompt",
    "secho",
]
