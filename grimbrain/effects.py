from __future__ import annotations

"""Very small timed effect engine used by the ``play`` CLI.

The engine keeps all state in a simple mapping supplied at construction time
so that callers can persist it inside their own data structures.  Each effect
is tracked per owner and is evaluated at either the start or the end of a
turn.  Effects can apply deterministic damage (positive) or healing
(negative) and may add or remove tags on the affected actor while active.

The engine itself is intentionally tiny – it only supports the features that
the tests exercise.  It is sufficient for demonstrating how timed effects can
be scheduled from rules and processed by the game loop in a deterministic
fashion.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TimedEffect:
    """Description of an effect with a fixed duration."""

    id: str
    owner_id: str  # actor that the effect is applied to
    source_rule: str
    timing: str  # ``start_of_turn`` or ``end_of_turn``
    duration_rounds: int
    remaining_rounds: int
    tag_add: Optional[str] = None
    tag_remove_on_expire: Optional[str] = None
    fixed_damage: Optional[int] = None  # positive=damage, negative=heal
    meta: Dict[str, Any] = field(default_factory=dict)


class EffectEngine:
    """Minimal in-memory effect tracker."""

    def __init__(self, state: Dict[str, Any]):
        self.state = state
        # Map of ``actor_id`` -> list of serialized effects
        self.state.setdefault("timed_effects", {})

    # ------------------------------------------------------------------
    # effect management helpers
    def add_effect(self, effect: TimedEffect) -> Dict[str, Any]:
        """Register ``effect`` and return an ``effect_started`` event."""

        bucket = self.state["timed_effects"].setdefault(effect.owner_id, [])
        bucket.append(effect.__dict__.copy())
        return {
            "kind": "effect_started",
            "owner": effect.owner_id,
            "effect_id": effect.id,
            "rule": effect.source_rule,
            "remaining": effect.remaining_rounds,
        }

    # ------------------------------------------------------------------
    def _iter_effects(self, actor_id: str):
        for eff in self.state["timed_effects"].get(actor_id, []):
            yield eff

    def _prune(self, actor_id: str) -> None:
        self.state["timed_effects"][actor_id] = [
            e for e in self.state["timed_effects"].get(actor_id, [])
            if e["remaining_rounds"] > 0
        ]

    # ------------------------------------------------------------------
    def on_turn_hook(
        self,
        actor_id: str,
        hook: str,
        apply_damage_cb,
        add_tag_cb,
        remove_tag_cb,
    ) -> List[Dict[str, Any]]:
        """Process effects for ``actor_id`` at the specified hook.

        ``hook`` must be ``"start_of_turn"`` or ``"end_of_turn"``.  The
        callbacks are invoked for deterministic damage/healing and for tag
        mutations.  The method returns a list of JSON-style events describing
        what happened.
        """

        events: List[Dict[str, Any]] = []
        any_changed = False
        for eff in list(self._iter_effects(actor_id)):
            if eff.get("timing") != hook:
                continue
            if eff.get("fixed_damage"):
                apply_damage_cb(actor_id, int(eff["fixed_damage"]))
                events.append(
                    {
                        "kind": "effect_tick",
                        "owner": actor_id,
                        "effect_id": eff["id"],
                        "delta_hp": -int(eff["fixed_damage"]),
                        "remaining": eff["remaining_rounds"],
                    }
                )
            eff["remaining_rounds"] -= 1
            any_changed = True
            if eff["remaining_rounds"] <= 0:
                if eff.get("tag_remove_on_expire"):
                    remove_tag_cb(actor_id, eff["tag_remove_on_expire"])
                events.append(
                    {
                        "kind": "effect_expired",
                        "owner": actor_id,
                        "effect_id": eff["id"],
                    }
                )
        if any_changed:
            self._prune(actor_id)
        return events

