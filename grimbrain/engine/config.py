"""Local configuration and caching utilities for Grimbrain."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Iterator


CONFIG_DIR = Path.home() / ".grimbrain"
DOTENV_PATH = CONFIG_DIR / ".env"
CACHE_DIR = CONFIG_DIR / "cache"
NARRATION_CACHE = CACHE_DIR / "narration.jsonl"

# Allow reading an adjacent project-level .env (useful for development setups).
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROJECT_DOTENV = PROJECT_ROOT / ".env"
LEGACY_CONFIG_PATHS = [CONFIG_DIR / "config.json", PROJECT_ROOT / "config.json"]


def _parse_dotenv(text: str) -> Dict[str, str]:
    data: Dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if value and value[0] in {'"', "'"} and value[-1:] == value[0]:
            value = value[1:-1]
        data[key] = value
    return data


def _format_dotenv(cfg: Dict[str, Any]) -> str:
    lines = []
    items: list[tuple[str, Any]] = []
    for key, value in cfg.items():
        if key is None:
            continue
        items.append((str(key), value))
    for key, value in sorted(items, key=lambda kv: kv[0]):
        if value is None:
            continue
        text = str(value)
        needs_quotes = any(ch in text for ch in "\n#'\" ")
        if needs_quotes:
            escaped = text.replace("\"", r"\"")
            text = f'"{escaped}"'
        lines.append(f"{key}={text}")
    return "\n".join(lines) + ("\n" if lines else "")


def load_config() -> Dict[str, Any]:
    """Load key/value pairs from available dotenv files."""

    data: Dict[str, Any] = {}
    for path in (PROJECT_DOTENV, DOTENV_PATH):
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            continue
        except OSError:
            continue
        data.update(_parse_dotenv(text))
    for legacy in LEGACY_CONFIG_PATHS:
        try:
            import json

            raw = legacy.read_text(encoding="utf-8")
            loaded = json.loads(raw)
        except FileNotFoundError:
            continue
        except OSError:
            continue
        except Exception:
            continue
        if isinstance(loaded, dict):
            for key, value in loaded.items():
                data.setdefault(key, value)
    return data


def save_config(cfg: Dict[str, Any]) -> None:
    """Persist *cfg* values to the local dotenv file."""

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    DOTENV_PATH.write_text(_format_dotenv(cfg), encoding="utf-8")


def get_api_key() -> str | None:
    """Return the API key using environment variable then dotenv precedence."""

    key = os.getenv("OPENAI_API_KEY")
    if key:
        return key
    cfg = load_config()
    for candidate in ("OPENAI_API_KEY", "openai_api_key"):
        value = cfg.get(candidate)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def append_cache_line(path: Path, obj: Dict[str, Any]) -> None:
    """Append a JSON line representing *obj* to *path*, creating parents."""

    import json

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(obj, ensure_ascii=False) + "\n")


def iter_cache(path: Path) -> Iterator[Dict[str, Any]]:
    """Yield JSON objects from a newline-delimited cache file."""

    import json

    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if isinstance(obj, dict):
                yield obj
