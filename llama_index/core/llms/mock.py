"""Mock LLM used for offline tests."""

from __future__ import annotations


class MockLLM:
    """Very small stub with an inspectable call history."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def predict(self, prompt: str) -> str:
        self.calls.append(prompt)
        return ""


__all__ = ["MockLLM"]
