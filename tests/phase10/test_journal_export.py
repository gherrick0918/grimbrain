"""Tests for journal formatting and export helpers."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from grimbrain.engine.journal import (
    export_journal_md,
    export_journal_txt,
    format_entries,
    log_event,
    write_export,
)


class _StubState:
    day = 1
    time_of_day = "dawn"
    location = "Road"

    def __init__(self) -> None:
        self.journal: list[dict[str, object]] = []


def _state() -> _StubState:
    return _StubState()


def test_formatters_and_export() -> None:
    st = _state()
    log_event(st, "Travel 4h; No encounter", kind="travel", extra={"effective": 30})
    log_event(st, "Short rest", kind="rest", extra={"type": "short"})

    lines = format_entries(st.journal, style="compact")
    assert len(lines) == 2
    assert "Travel 4h" in lines[0]

    detailed = format_entries(st.journal, style="detailed")
    assert any("Kind: rest" in line for line in detailed[1].splitlines())

    md = export_journal_md(st.journal)
    assert "# Adventure Journal" in md and "- [Day 1" in md

    txt = export_journal_txt(st.journal, style="detailed")
    assert "Kind: rest" in txt

    with tempfile.TemporaryDirectory() as tmpdir:
        txt_path = os.path.join(tmpdir, "journal.txt")
        md_path = os.path.join(tmpdir, "journal.md")
        write_export(st.journal, txt_path, style="compact")
        write_export(st.journal, md_path, style="detailed")
        assert os.path.exists(txt_path)
        assert os.path.exists(md_path)
        md_contents = Path(md_path).read_text(encoding="utf-8")
        assert "Adventure Journal" in md_contents
