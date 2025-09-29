from __future__ import annotations

import contextlib
import dataclasses
import datetime as _dt
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Callable, Mapping, MutableMapping, Sequence

CACHE_VERSION = 2
_INDEX_FILENAME = "index.json"
_LOCK_FILENAME = "index.lock"
_TEXT_SUFFIX = ".txt"
_DEFAULT_PARAM_KEYS = (
    "temperature",
    "top_p",
    "presence_penalty",
    "frequency_penalty",
    "seed",
)


@dataclasses.dataclass(frozen=True)
class CacheInputs:
    """Inputs that uniquely identify an AI completion request."""

    model: str
    messages: Sequence[Mapping[str, Any]]
    tools: Sequence[Mapping[str, Any]] | None = None
    params: Mapping[str, Any] | None = None
    style: str | None = None


def call_with_cache(inputs: CacheInputs, fn_call_model: Callable[[], str]) -> str:
    """Return cached response text for identical inputs, calling ``fn_call_model``
    only on cache miss (or refresh)."""

    if _is_cache_disabled():
        return fn_call_model()

    cache_dir = _cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = make_cache_key(inputs)
    text_path = cache_dir / f"{key}{_TEXT_SUFFIX}"
    refresh = _refresh_requested()

    with _index_lock(cache_dir):
        index = _load_index(cache_dir)
        entry = index.get("entries", {}).get(key)
        entry = _validate_entry(cache_dir, key, entry)
        ttl_expired = _ttl_expired(entry)
        if entry and not refresh and not ttl_expired:
            try:
                text = text_path.read_text(encoding="utf-8")
            except FileNotFoundError:
                _log("STALE-INDEX", key)
                _remove_entry(index, key)
            else:
                _touch_entry(entry)
                _save_index(cache_dir, index)
                _log("HIT", key, hits=entry.get("hits"))
                return text
        if entry and (refresh or ttl_expired):
            _remove_entry(index, key)

        text = fn_call_model()
        _write_text_atomic(text_path, text)
        entry = _create_entry(inputs, text_path)
        index.setdefault("entries", {})[key] = entry
        _enforce_limits(cache_dir, index)
        _save_index(cache_dir, index)
        _log("MISS→WRITE", key, hits=entry.get("hits"))
        return text


def make_cache_key(inputs: CacheInputs) -> str:
    payload = {
        "model": (inputs.model or ""),
        "messages": _canonical_messages(inputs.messages),
        "tools": _canonical_tools(inputs.tools),
        "params": _canonical_params(inputs.params),
        "style": inputs.style or None,
    }
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Index helpers


def _cache_dir() -> Path:
    env_dir = os.environ.get("GRIMBRAIN_AI_CACHE_DIR")
    if env_dir:
        return Path(env_dir)
    return Path.home() / ".grimbrain_cache"


def _index_path(cache_dir: Path) -> Path:
    return cache_dir / _INDEX_FILENAME


@contextlib.contextmanager
def _index_lock(cache_dir: Path):
    path = cache_dir / _LOCK_FILENAME
    cache_dir.mkdir(parents=True, exist_ok=True)
    with open(path, "a+b") as lock_file:
        _lock_file(lock_file)
        try:
            yield
        finally:
            _unlock_file(lock_file)


def _load_index(cache_dir: Path) -> MutableMapping[str, Any]:
    index_path = _index_path(cache_dir)
    if not index_path.exists():
        return {"version": CACHE_VERSION, "entries": {}}
    try:
        data = json.loads(index_path.read_text(encoding="utf-8"))
    except Exception:
        return {"version": CACHE_VERSION, "entries": {}}
    if data.get("version") != CACHE_VERSION:
        return {"version": CACHE_VERSION, "entries": {}}
    entries = data.get("entries")
    if not isinstance(entries, dict):
        entries = {}
    _drop_missing_files(cache_dir, entries)
    data["entries"] = entries
    return data


def _save_index(cache_dir: Path, index: Mapping[str, Any]) -> None:
    index_path = _index_path(cache_dir)
    payload = json.dumps(index, indent=2, ensure_ascii=False)
    _write_text_atomic(index_path, payload, binary=True)


def _drop_missing_files(cache_dir: Path, entries: MutableMapping[str, Any]) -> None:
    missing: list[str] = []
    for key, entry in list(entries.items()):
        filename = entry.get("filename")
        if not filename:
            missing.append(key)
            continue
        path = cache_dir / filename
        if not path.exists():
            missing.append(key)
    for key in missing:
        entries.pop(key, None)


def _validate_entry(cache_dir: Path, key: str, entry: Mapping[str, Any] | None):
    if not entry:
        return None
    filename = entry.get("filename")
    if not filename:
        return None
    path = cache_dir / filename
    if not path.exists():
        _log("STALE-INDEX", key)
        return None
    return entry


def _remove_entry(index: MutableMapping[str, Any], key: str) -> None:
    entries = index.get("entries")
    if isinstance(entries, dict):
        entries.pop(key, None)


def _touch_entry(entry: MutableMapping[str, Any]) -> None:
    now = _now()
    entry["last_hit_at"] = now
    entry["hits"] = int(entry.get("hits", 0)) + 1


def _create_entry(inputs: CacheInputs, path: Path) -> dict[str, Any]:
    now = _now()
    size = path.stat().st_size if path.exists() else 0
    return {
        "filename": path.name,
        "model": inputs.model,
        "created_at": now,
        "last_hit_at": now,
        "hits": 1,
        "size": size,
    }


def _enforce_limits(cache_dir: Path, index: MutableMapping[str, Any]) -> None:
    entries = index.get("entries")
    if not isinstance(entries, dict):
        return
    max_bytes = _max_bytes()
    if max_bytes <= 0:
        return
    def _entry_size(item: tuple[str, Mapping[str, Any]]) -> int:
        return int(item[1].get("size") or 0)

    total = sum(_entry_size(item) for item in entries.items())
    if total <= max_bytes:
        return
    sorted_items = sorted(
        entries.items(),
        key=lambda kv: (
            kv[1].get("last_hit_at") or kv[1].get("created_at") or "",
            kv[0],
        ),
    )
    for key, entry in sorted_items:
        filename = entry.get("filename")
        if filename:
            path = cache_dir / filename
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        entries.pop(key, None)
        total -= int(entry.get("size") or 0)
        if total <= max_bytes:
            break


# ---------------------------------------------------------------------------
# Canonicalization


def _canonical_messages(messages: Sequence[Mapping[str, Any]]) -> list[Any]:
    canonical: list[Any] = []
    for message in messages or []:
        allowed = {
            key: message.get(key)
            for key in ("role", "content", "name", "tool_call_id", "tool_calls")
            if key in message
        }
        canonical.append(_canonicalize(allowed))
    return canonical


def _canonical_tools(tools: Sequence[Mapping[str, Any]] | None) -> list[Any] | None:
    if tools is None:
        return None
    return [_canonicalize(tool) for tool in tools]


def _canonical_params(params: Mapping[str, Any] | None) -> Mapping[str, Any]:
    result: dict[str, Any] = {}
    for key in _DEFAULT_PARAM_KEYS:
        result[key] = params.get(key) if params else None
    if params:
        for key in sorted(params.keys()):
            if key not in result:
                result[key] = params[key]
    return _canonicalize(result)


def _canonicalize(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace("\r\n", "\n").replace("\r", "\n")
    if isinstance(value, Mapping):
        return {k: _canonicalize(value[k]) for k in sorted(value)}
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return [_canonicalize(item) for item in value]
    return value


# ---------------------------------------------------------------------------
# Misc helpers


def _write_text_atomic(path: Path, text: str, *, binary: bool = False) -> None:
    if binary:
        data = text.encode("utf-8") if isinstance(text, str) else text
    else:
        data = text.encode("utf-8")
    tmp_fd, tmp_path = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp_path, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp_path)


def _is_cache_disabled() -> bool:
    return os.environ.get("GRIMBRAIN_AI_DISABLE_CACHE") == "1"


def _refresh_requested() -> bool:
    return os.environ.get("GRIMBRAIN_AI_REFRESH_CACHE") == "1"


def _max_bytes() -> int:
    try:
        return int(os.environ.get("GRIMBRAIN_AI_CACHE_MAX_BYTES", "0"))
    except (TypeError, ValueError):
        return 0


def _ttl_days() -> int:
    try:
        return int(os.environ.get("GRIMBRAIN_AI_CACHE_TTL_DAYS", "0"))
    except (TypeError, ValueError):
        return 0


def _ttl_expired(entry: Mapping[str, Any] | None) -> bool:
    if not entry:
        return False
    days = _ttl_days()
    if days <= 0:
        return False
    created_at = entry.get("created_at")
    if not isinstance(created_at, str):
        return True
    try:
        created = _dt.datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except ValueError:
        return True
    return (_dt.datetime.now(tz=_dt.timezone.utc) - created) > _dt.timedelta(days=days)


def _now() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).replace(microsecond=0).isoformat()


def _log(event: str, key: str, *, hits: Any | None = None) -> None:
    import sys

    message = f"AI cache {event} key={key}"
    if hits is not None:
        message += f" hits={hits}"
    print(message, file=sys.stderr)


def _lock_file(handle) -> None:
    if os.name == "nt":  # pragma: no cover - Windows CI not used, but keep logic
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
    else:  # pragma: no branch
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)


def _unlock_file(handle) -> None:
    if os.name == "nt":  # pragma: no cover
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:  # pragma: no branch
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
