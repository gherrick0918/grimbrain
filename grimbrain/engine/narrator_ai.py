"""AI narrator implementation that integrates with OpenAI's Responses API."""

from __future__ import annotations

import json
import urllib.request
from typing import Any, Dict

from .narrator import TemplateNarrator

SYSTEM = (
    "You are a concise fantasy narrator. Keep output 1-3 short sentences. "
    "Do not reveal meta data; speak diegetically. Avoid spoilers."
)


class AINarrator:
    """Narrator that requests prose from a remote model."""

    KIND = "openai:gpt-4o-mini"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def render(self, template: str, ctx: Dict[str, Any]) -> str:  # type: ignore[override]
        """Render narration using the AI backend, falling back to templates."""

        prompt = TemplateNarrator().render(template, ctx)
        try:
            body = {
                "model": "gpt-4o-mini",
                "input": [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                "max_output_tokens": 120,
                "temperature": 0.7,
            }
            request = urllib.request.Request(
                "https://api.openai.com/v1/responses",
                data=json.dumps(body).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))
            text = ""
            for item in payload.get("output", []):
                if isinstance(item, dict):
                    for chunk in item.get("content", []) or []:
                        if isinstance(chunk, dict) and chunk.get("type") == "output_text":
                            text += chunk.get("text", "")
            text = text.strip()
            return text or prompt
        except Exception:
            return TemplateNarrator().render(template, ctx)
