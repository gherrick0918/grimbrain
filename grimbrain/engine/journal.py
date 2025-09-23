"""Journal logging utilities for campaign state."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List


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


def _compact_line(entry: Dict[str, Any]) -> str:
    """Render a single journal entry as a compact one-liner."""

    day = entry.get("day")
    when = entry.get("time")
    loc = entry.get("loc")
    kind = entry.get("kind", "info")
    text = entry.get("text", "")
    return f"[Day {day} {when} @ {loc}] ({kind}) {text}"


def _detailed_block(entry: Dict[str, Any]) -> str:
    """Render a single journal entry as a detailed block."""

    ts = entry.get("ts", "")
    day = entry.get("day")
    when = entry.get("time")
    loc = entry.get("loc")
    kind = entry.get("kind", "info")
    text = entry.get("text", "")
    extra = entry.get("extra") or {}

    lines = [f"[{ts}] Day {day} {when} @ {loc}", f"  Kind: {kind}", f"  Text: {text}"]
    if extra:
        for key in sorted(extra.keys()):
            lines.append(f"  {key}: {extra[key]}")
    return "\n".join(lines)


def format_entries(entries: Iterable[Dict[str, Any]], *, style: str = "compact") -> List[str]:
    """Format a sequence of journal entries according to the requested style."""

    formatter = _detailed_block if style == "detailed" else _compact_line
    return [formatter(entry) for entry in entries]


def export_journal_md(entries: Iterable[Dict[str, Any]]) -> str:
    """Export the journal as Markdown grouped by day."""

    grouped: Dict[int, List[Dict[str, Any]]] = {}
    for entry in entries:
        day = int(entry.get("day", 0))
        grouped.setdefault(day, []).append(entry)

    parts: List[str] = ["# Adventure Journal"]
    for day in sorted(grouped.keys()):
        parts.append("\n## Day {day}".format(day=day))
        for entry in grouped[day]:
            parts.append(f"- {_compact_line(entry)}")
    parts.append("")
    return "\n".join(parts)


def export_journal_txt(entries: Iterable[Dict[str, Any]], *, style: str = "compact") -> str:
    """Export the journal to plain text using the requested style."""

    entries_list = list(entries)
    body = "\n".join(format_entries(entries_list, style=style))
    if entries_list:
        body += "\n"
    return body


def write_export(entries: Iterable[Dict[str, Any]], path: str, *, style: str = "compact") -> None:
    """Write the journal export to ``path`` based on its extension."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    entries_list = list(entries)
    if target.suffix.lower() == ".md":
        content = export_journal_md(entries_list)
    else:
        content = export_journal_txt(entries_list, style=style)
    target.write_text(content, encoding="utf-8")
