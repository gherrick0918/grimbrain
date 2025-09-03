from dataclasses import dataclass, field
from typing import Optional, Literal, Set

Cover = Literal["none", "half", "three-quarters", "total"]


@dataclass
class DeathState:
    successes: int = 0
    failures: int = 0
    stable: bool = False
    dead: bool = False


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
    death: DeathState = field(default_factory=DeathState)  # per-combat state
    resist: Set[str] = field(default_factory=set)
    vulnerable: Set[str] = field(default_factory=set)
    immune: Set[str] = field(default_factory=set)
    temp_hp: int = 0
