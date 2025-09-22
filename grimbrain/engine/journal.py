"""Journal logging utilities for campaign state."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict


def _ensure_journal(state: Any) -> list[Dict[str, Any]]:
    journal = getattr(state, "journal", None)
    if journal is None:
        journal = []
        setattr(state, "journal", journal)
    return journal


def log_event(
    state: Any,
    text: str,
    *,
    kind: str = "info",
    extra: Dict[str, Any] | None = None,
) -> None:
    """Append a single journal entry including campaign context."""

    journal = _ensure_journal(state)
    entry: Dict[str, Any] = {
        "ts": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "day": getattr(state, "day", 1),
        "time": getattr(state, "time_of_day", "morning"),
        "loc": getattr(state, "location", "Wilderness"),
        "kind": kind,
        "text": text.strip(),
    }
    if extra:
        entry["extra"] = extra
    journal.append(entry)
