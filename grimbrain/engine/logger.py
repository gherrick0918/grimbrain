from __future__ import annotations

import json
from pathlib import Path


class SessionLogger:
    """Write parallel JSONL and Markdown event logs."""

    def __init__(self, path_base: str | Path):
        base = Path(path_base)
        if base.suffix:
            base = base.with_suffix("")
        self.jsonl = base.with_suffix(".jsonl")
        self.md = base.with_suffix(".md")
        self.jsonl.parent.mkdir(parents=True, exist_ok=True)
        self.md.parent.mkdir(parents=True, exist_ok=True)
        # ensure files exist
        self.jsonl.touch()
        self.md.touch()

    def log_event(self, event_type: str, **data) -> None:
        event = {"type": event_type, **data}
        with self.jsonl.open("a", encoding="utf-8") as jf:
            jf.write(json.dumps(event) + "\n")
        with self.md.open("a", encoding="utf-8") as mf:
            if event_type == "narration":
                mf.write(f"{data.get('text', '')}\n")
            elif event_type == "choice":
                mf.write(f"* choice {data.get('choice')} -> {data.get('next')}\n")
            elif event_type == "encounter":
                mf.write(
                    f"* encounter {data.get('enemy')} -> {data.get('result')} ({data.get('summary')})\n"
                )
            else:
                mf.write(f"* {event_type}\n")
