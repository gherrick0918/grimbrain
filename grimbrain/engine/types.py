from dataclasses import dataclass
from typing import Optional, Literal

Cover = Literal["none", "half", "three-quarters", "total"]


@dataclass
class Target:
    ac: int
    hp: int
    cover: Cover = "none"
    distance_ft: Optional[int] = None


@dataclass
class Combatant:
    name: str
    # Minimal fields used by the engine (Character-like)
    actor: object     # your Character
    hp: int
    weapon: str
    # Optional extras
    offhand: Optional[str] = None
    distance_ft: Optional[int] = None
    cover: Cover = "none"
