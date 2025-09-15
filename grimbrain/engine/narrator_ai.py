"""Placeholder AI narrator implementation."""

from __future__ import annotations


class AINarrator:
    """Stub narrator that currently defers to the local template renderer."""

    def render(self, template: str, ctx):  # type: ignore[override]
        # A future implementation can call an external model here. For now we
        # fall back to the template narrator so that behaviour remains local and
        # deterministic when AI mode is enabled.
        from .narrator import TemplateNarrator

        return TemplateNarrator().render(template, ctx)
