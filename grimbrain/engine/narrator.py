"""Narration utilities for rendering scene text."""

from __future__ import annotations

import hashlib
import os
from typing import Any, Dict

from .config import (
    NARRATION_CACHE,
    append_cache_line,
    get_api_key,
    iter_cache,
)


class TemplateNarrator:
    """Simple, local narrator that performs inline template replacement."""

    KIND = "template"

    def render(self, template: str, ctx: Dict[str, object]) -> str:
        """Render *template* by replacing ``{{key}}`` tokens using *ctx* values."""

        out = template or ""
        for key, value in ctx.items():
            out = out.replace(f"{{{{{key}}}}}", str(value))
        return out


def _hash(scene_id: str, template: str, ctx: Dict[str, Any], kind: str) -> str:
    """Create a stable hash for the given narration inputs."""

    digest = hashlib.sha256()
    digest.update(kind.encode("utf-8", "ignore"))
    digest.update(b"\x00")
    digest.update(scene_id.encode("utf-8", "ignore"))
    digest.update(b"\x00")
    digest.update((template or "").encode("utf-8", "ignore"))
    digest.update(b"\x00")
    digest.update(str(sorted(ctx.items())).encode("utf-8", "ignore"))
    return digest.hexdigest()


class CachedNarrator:
    """Wrap a narrator backend with simple on-disk caching."""

    def __init__(self, backend, debug: bool = False) -> None:
        self.backend = backend
        self.debug = debug
        self.kind = getattr(backend, "KIND", "template")

    def render(self, scene_id: str, template: str, ctx: Dict[str, Any]) -> str:
        key = _hash(scene_id, template, ctx, self.kind)
        for row in iter_cache(NARRATION_CACHE):
            if row.get("key") == key:
                if self.debug:
                    print(f"[narration] ai={self.kind} cache=HIT scene={scene_id}")
                return str(row.get("text", ""))
        text = self.backend.render(template, ctx)
        append_cache_line(
            NARRATION_CACHE, {"key": key, "text": text, "kind": self.kind}
        )
        if self.debug:
            print(f"[narration] ai={self.kind} cache=MISS scene={scene_id}")
        return text


def get_narrator(debug: bool = False):
    """Return the active narrator implementation.

    The local template narrator is always available. An AI-backed narrator can be
    enabled by setting ``GRIMBRAIN_AI=1`` along with an API key (environment
    variable or .env entry). If the AI narrator cannot be initialised we
    silently fall back to the local implementation, while still using the cache
    layer for determinism.
    """

    testing = bool(
        os.getenv("PYTEST_CURRENT_TEST")
        or os.getenv("GB_TESTING") == "1"
        or os.getenv("IS_TESTING") == "1"
    )
    use_ai = os.getenv("GRIMBRAIN_AI") == "1" and not testing
    key = get_api_key()
    if use_ai and key:
        try:
            from .narrator_ai import AINarrator

            return CachedNarrator(AINarrator(api_key=key), debug=debug)
        except Exception:
            pass
    return CachedNarrator(TemplateNarrator(), debug=debug)
