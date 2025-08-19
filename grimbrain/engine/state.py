"""State helper functions for death and dying."""
from __future__ import annotations


def set_dying(actor: dict) -> None:
    actor["dying"] = True
    actor["stable"] = False


def set_stable(actor: dict) -> None:
    actor["dying"] = False
    actor["stable"] = True


def clear_death_saves(actor: dict) -> None:
    actor["death_failures"] = 0


def add_death_failure(actor: dict, n: int = 1) -> None:
    actor["death_failures"] = actor.get("death_failures", 0) + n
    if actor["death_failures"] >= 3:
        actor["dead"] = True
