"""Minimal YAML subset loader/dumper for offline test environments."""
from __future__ import annotations

from typing import Any, Iterable, Tuple


class YAMLError(Exception):
    """Fallback error type for compatibility with PyYAML."""


def safe_load(text: str) -> Any:
    lines = _prepare_lines(text)
    if not lines:
        return None
    value, index = _parse_block(lines, 0, 0)
    if index != len(lines):
        # best-effort: ignore trailing whitespace/comments already stripped
        pass
    return value


def safe_dump(data: Any, sort_keys: bool = False, indent: int = 2) -> str:
    return "\n".join(_dump_lines(data, 0, sort_keys=sort_keys, indent=indent)) + "\n"


# ---------------------------------------------------------------------------
# PyYAML compatibility aliases
# ---------------------------------------------------------------------------


dump = safe_dump
load = safe_load
safe_load_all = lambda text: [safe_load(text)]
safe_dump_all = lambda seq, **kwargs: "".join(safe_dump(item, **kwargs) for item in seq)


# --- parsing helpers -----------------------------------------------------


def _prepare_lines(text: str) -> list[str]:
    prepared: list[str] = []
    for raw in text.splitlines():
        stripped = raw.rstrip()
        if not stripped:
            continue
        temp = []
        in_quote: str | None = None
        for ch in stripped:
            if ch in {'"', "'"}:
                if in_quote == ch:
                    in_quote = None
                elif in_quote is None:
                    in_quote = ch
            if ch == "#" and in_quote is None:
                break
            temp.append(ch)
        cleaned = "".join(temp).rstrip()
        if not cleaned:
            continue
        prepared.append(cleaned)
    return prepared


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _parse_block(lines: list[str], index: int, indent: int) -> Tuple[Any, int]:
    seq: list[Any] = []
    mapping: dict[str, Any] = {}
    mode: str | None = None
    length = len(lines)
    while index < length:
        line = lines[index]
        current_indent = _indent_of(line)
        if current_indent < indent:
            break
        if current_indent > indent and mode is None:
            raise ValueError(f"Unexpected indent at line: {line!r}")
        stripped = line.strip()
        if stripped.startswith("- "):
            if mode == "mapping":
                break
            mode = "sequence"
            value, index = _parse_sequence_item(lines, index, indent)
            seq.append(value)
        else:
            if mode == "sequence":
                break
            mode = "mapping"
            key, value, index = _parse_mapping_entry(lines, index, indent)
            mapping[key] = value
    if mode == "sequence":
        return seq, index
    return mapping, index


def _parse_sequence_item(lines: list[str], index: int, indent: int) -> Tuple[Any, int]:
    line = lines[index]
    current_indent = _indent_of(line)
    if current_indent != indent:
        raise ValueError(f"Sequence indent mismatch at line: {line!r}")
    stripped = line.strip()[2:].strip()
    index += 1
    if not stripped:
        value, index = _parse_block(lines, index, indent + 2)
        return value, index
    if stripped.endswith(":"):
        key = stripped[:-1].strip()
        nested, index = _parse_block(lines, index, indent + 2)
        return {key: nested}, index
    if ":" in stripped:
        key, rest = stripped.split(":", 1)
        key = key.strip()
        rest = rest.strip()
        entry: dict[str, Any] = {}
        if rest:
            entry[key] = _parse_scalar(rest)
        else:
            nested, index = _parse_block(lines, index, indent + 2)
            entry[key] = nested
            return entry, index
        while index < len(lines):
            next_line = lines[index]
            next_indent = _indent_of(next_line)
            if next_indent <= indent:
                break
            if next_indent < indent + 2:
                break
            if next_indent > indent + 2:
                value, index = _parse_block(lines, index, indent + 2)
                if isinstance(value, dict):
                    entry.update(value)
                else:
                    entry[key] = value
                return entry, index
            k2, v2, index = _parse_mapping_entry(lines, index, indent + 2)
            entry[k2] = v2
        return entry, index
    value = _parse_scalar(stripped)
    return value, index


def _parse_mapping_entry(lines: list[str], index: int, indent: int) -> Tuple[str, Any, int]:
    line = lines[index]
    current_indent = _indent_of(line)
    if current_indent != indent:
        raise ValueError(f"Mapping indent mismatch at line: {line!r}")
    stripped = line.strip()
    if ":" not in stripped:
        raise ValueError(f"Expected ':' in mapping entry: {line!r}")
    key, rest = stripped.split(":", 1)
    key = key.strip()
    rest = rest.strip()
    index += 1
    if rest:
        value = _parse_scalar(rest)
    else:
        value, index = _parse_block(lines, index, indent + 2)
    return key, value, index


def _parse_scalar(token: str) -> Any:
    lowered = token.lower()
    if lowered in {"null", "none"}:
        return None
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if token == "[]":
        return []
    if token == "{}":
        return {}
    if token.startswith("[") and token.endswith("]"):
        inner = token[1:-1].strip()
        if not inner:
            return []
        parts = [p.strip() for p in inner.split(",")]
        return [
            _parse_scalar(part[1:-1] if part.startswith('"') and part.endswith('"') else part)
            for part in parts
        ]
    try:
        if token.startswith("0") and len(token) > 1 and token[1].isdigit():
            raise ValueError
        return int(token)
    except ValueError:
        pass
    try:
        return float(token)
    except ValueError:
        pass
    if (token.startswith('"') and token.endswith('"')) or (
        token.startswith("'") and token.endswith("'")
    ):
        inner = token[1:-1]
        inner = inner.replace("\\'", "'").replace('\\"', '"')
        return inner
    return token


# --- dumping helpers -----------------------------------------------------


def _dump_lines(data: Any, indent_level: int, *, sort_keys: bool, indent: int) -> list[str]:
    pad = " " * indent_level
    if isinstance(data, dict):
        lines: list[str] = []
        keys: Iterable[str]
        if sort_keys:
            keys = sorted(data.keys())
        else:
            keys = data.keys()
        for key in keys:
            value = data[key]
            if isinstance(value, (dict, list)):
                lines.append(f"{pad}{key}:")
                lines.extend(
                    _dump_lines(value, indent_level + indent, sort_keys=sort_keys, indent=indent)
                )
            else:
                lines.append(f"{pad}{key}: {_format_scalar(value)}")
        return lines
    if isinstance(data, list):
        lines = []
        for item in data:
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}-")
                lines.extend(
                    _dump_lines(item, indent_level + indent, sort_keys=sort_keys, indent=indent)
                )
            else:
                lines.append(f"{pad}- {_format_scalar(item)}")
        if not lines:
            lines.append(f"{pad}[]")
        return lines
    return [f"{pad}{_format_scalar(data)}"]


def _format_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if any(ch in text for ch in [":", "#", "\"", "'", "\n"]):
        escaped = text.replace("\\", "\\\\").replace("\"", "\\\"")
        return f'"{escaped}"'
    return text


__all__ = [
    "safe_load",
    "safe_dump",
    "load",
    "dump",
    "safe_load_all",
    "safe_dump_all",
    "YAMLError",
]
