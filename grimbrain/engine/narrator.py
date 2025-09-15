"""Narration utilities for rendering scene text."""

from __future__ import annotations

import os
from typing import Dict


class TemplateNarrator:
    """Simple, local narrator that performs inline template replacement."""

    def render(self, template: str, ctx: Dict[str, object]) -> str:
        """Render *template* by replacing ``{{key}}`` tokens using *ctx* values."""

        out = template
        for key, value in ctx.items():
            out = out.replace(f"{{{{{key}}}}}", str(value))
        return out


def get_narrator():
    """Return the active narrator implementation.

    The local template narrator is always available. An AI-backed narrator can be
    enabled by setting ``GRIMBRAIN_AI=1`` along with an API key environment
    variable. If the AI narrator cannot be initialised we silently fall back to
    the local implementation.
    """

    if os.getenv("GRIMBRAIN_AI") == "1" and (
        os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    ):
        try:
            from .narrator_ai import AINarrator

            return AINarrator()
        except Exception:
            pass
    return TemplateNarrator()
