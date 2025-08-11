"""Minimal session loop scaffold with save/load support."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

from query_router import run_query

LOG_DIR = Path("logs")


@dataclass
class Session:
    scene: str
    seed: int | None = None
    steps: List[dict] = field(default_factory=list)

    @classmethod
    def start(cls, scene: str, seed: int | None = None) -> "Session":
        if seed is None:
            seed = int(datetime.now().timestamp())
        return cls(scene=scene, seed=seed)

    def log_step(self, prompt: str, resolution: str) -> None:
        self.steps.append({"prompt": prompt, "resolution": resolution})

    def save(self, path: str | Path) -> Path:
        """Write session data to ``path``."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {"seed": self.seed, "scene": self.scene, "steps": self.steps}
        path.write_text(json.dumps(data, indent=2))
        return path

    @classmethod
    def load(cls, path: str | Path) -> "Session":
        data = json.loads(Path(path).read_text())
        return cls(scene=data.get("scene", ""), seed=data.get("seed"), steps=data.get("steps", []))


def _log_paths() -> Tuple[Path, Path]:
    LOG_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    md_path = LOG_DIR / f"session_{stamp}.md"
    json_path = LOG_DIR / f"session_{stamp}.json"
    return md_path, json_path


def start_scene(scene: str, seed: int | None = None) -> Tuple[Path, Path]:
    """Start a new scene and create paired markdown/JSON logs."""
    md_path, json_path = _log_paths()
    md_path.write_text(f"# Scene: {scene}\n")
    session = Session.start(scene, seed)
    session.save(json_path)
    return md_path, json_path


def log_step(md_path: Path, json_path: Path, prompt: str, resolution: str) -> None:
    """Append a prompt/resolution pair to the logs."""
    with md_path.open("a", encoding="utf-8") as md:
        md.write(f"\n## Prompt\n{prompt}\n\n## Resolution\n{resolution}\n")
    session = Session.load(json_path)
    session.log_step(prompt, resolution)
    session.save(json_path)


def lookup(kind: str, query: str, embed_model=None):
    """Convenience wrapper around :func:`run_query`."""
    return run_query(type=kind, query=query, embed_model=embed_model)
