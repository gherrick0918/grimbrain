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

    def render(self, template: str, ctx: Dict[str, object]) -> str:
        """Render *template* by replacing ``{{key}}`` tokens using *ctx* values."""

        out = template or ""
        for key, value in ctx.items():
            out = out.replace(f"{{{{{key}}}}}", str(value))
        return out


def _hash(scene_id: str, template: str, ctx: Dict[str, Any]) -> str:
    """Create a stable hash for the given narration inputs."""

    digest = hashlib.sha256()
    digest.update(scene_id.encode("utf-8", "ignore"))
    digest.update(b"\x00")
    digest.update((template or "").encode("utf-8", "ignore"))
    digest.update(b"\x00")
    digest.update(str(sorted(ctx.items())).encode("utf-8", "ignore"))
    return digest.hexdigest()


class CachedNarrator:
    """Wrap a narrator backend with simple on-disk caching."""

    def __init__(self, backend) -> None:
        self.backend = backend
        # Only persist and reuse cache entries for non-template backends.
        # The template narrator is deterministic and should always render the
        # literal scene text. Reusing cached AI prose while running in template
        # mode caused stale, flowery narration to bleed into tests that expect
        # the source YAML strings.
        self.use_cache = not isinstance(backend, TemplateNarrator)

    def render(self, scene_id: str, template: str, ctx: Dict[str, Any]) -> str:
        key = _hash(scene_id, template, ctx)
        if self.use_cache:
            for row in iter_cache(NARRATION_CACHE):
                if row.get("key") == key:
                    return str(row.get("text", ""))
        text = self.backend.render(template, ctx)
        if self.use_cache:
            append_cache_line(NARRATION_CACHE, {"key": key, "text": text})
        return text


def get_narrator():
    """Return the active narrator implementation.

    The local template narrator is always available. An AI-backed narrator can be
    enabled by setting ``GRIMBRAIN_AI=1`` along with an API key (environment
    variable or .env entry). If the AI narrator cannot be initialised we
    silently fall back to the local implementation, while still using the cache
    layer for determinism.
    """

    use_ai = os.getenv("GRIMBRAIN_AI") == "1"
    key = get_api_key()
    if use_ai and key:
        try:
            from .narrator_ai import AINarrator

            return CachedNarrator(AINarrator(api_key=key))
        except Exception:
            pass
    return CachedNarrator(TemplateNarrator())
