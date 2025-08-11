"""Minimal session loop scaffold.

Provides helpers to start a scene and append interactions. The goal is a
lightweight, append-only log that can later be expanded into a playable loop.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Tuple

from query_router import run_query

LOG_DIR = Path("logs")


def _log_paths() -> Tuple[Path, Path]:
    LOG_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    md_path = LOG_DIR / f"session_{stamp}.md"
    json_path = LOG_DIR / f"session_{stamp}.json"
    return md_path, json_path


def start_scene(scene: str) -> Tuple[Path, Path]:
    """Start a new scene and create paired markdown/JSON logs."""
    md_path, json_path = _log_paths()
    md_path.write_text(f"# Scene: {scene}\n")
    json_path.write_text(json.dumps({"scene": scene, "log": []}, indent=2))
    return md_path, json_path


def log_step(md_path: Path, json_path: Path, prompt: str, resolution: str) -> None:
    """Append a prompt/resolution pair to the logs."""
    with md_path.open("a", encoding="utf-8") as md:
        md.write(f"\n## Prompt\n{prompt}\n\n## Resolution\n{resolution}\n")
    try:
        data = json.loads(json_path.read_text())
    except Exception:
        data = {"scene": "", "log": []}
    data.setdefault("log", []).append({"prompt": prompt, "resolution": resolution})
    json_path.write_text(json.dumps(data, indent=2))


def lookup(kind: str, query: str, embed_model=None):
    """Convenience wrapper around :func:`run_query`."""
    return run_query(type=kind, query=query, embed_model=embed_model)
