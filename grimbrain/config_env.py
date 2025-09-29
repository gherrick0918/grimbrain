"""Helpers for loading project environment configuration."""

from __future__ import annotations

import os
from pathlib import Path


def load_env() -> None:
    """Load environment variables from .env files without overriding process env."""

    try:
        from dotenv import find_dotenv, load_dotenv
    except Exception:  # pragma: no cover - optional dependency or import error
        return

    cwd = Path.cwd()

    base = find_dotenv(".env", usecwd=True)
    if base:
        load_dotenv(base, override=False)

    local_file = cwd / ".env.local"
    if local_file.exists():
        load_dotenv(local_file, override=False)

    if os.getenv("PYTEST_CURRENT_TEST"):
        test_file = cwd / ".env.test"
        if test_file.exists():
            load_dotenv(test_file, override=False)

    cache_dir = os.getenv("GRIMBRAIN_AI_CACHE_DIR")
    if cache_dir:
        normalized = Path(cache_dir).expanduser()
        try:
            normalized = normalized.resolve()
        except OSError:
            pass
        os.environ["GRIMBRAIN_AI_CACHE_DIR"] = str(normalized)
