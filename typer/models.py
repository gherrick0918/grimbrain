"""Lightweight stand-ins for Typer parameter info structures."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Tuple


@dataclass
class OptionInfo:
    default: Any
    param_decls: Tuple[str, ...] = field(default_factory=tuple)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ArgumentInfo:
    default: Any
    param_decls: Tuple[str, ...] = field(default_factory=tuple)
    metadata: Dict[str, Any] = field(default_factory=dict)
