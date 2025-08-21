from __future__ import annotations

import os


def format_suggestion(item):
    show = os.environ.get("GB_SUGGESTIONS_SHOW_SCORES", "")
    if show and getattr(item, "score", None) is not None:
        return f"- {item.verb} {item.target_hint} [{item.score:.2f}]"
    return f"- {item.verb} {item.target_hint}"

