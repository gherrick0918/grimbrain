from dataclasses import dataclass, field
from typing import Optional, Literal, Set, Dict

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
    conditions: Set[str] = field(default_factory=set)


@dataclass
class Combatant:
    name: str
    # Minimal fields used by the engine (Character-like)
    actor: object     # your Character
    hp: int
    weapon: str
    # NEW: resting state
    max_hp: Optional[int] = None          # if None, treat as current hp at creation time
    hd_faces: int = 8                     # e.g., Fighter 10, Wizard 6
    hd_total: int = 1
    hd_remaining: int = 1
    # Optional extras
    offhand: Optional[str] = None
    distance_ft: Optional[int] = None
    cover: Cover = "none"
    conditions: Set[str] = field(default_factory=set)
    resist: Set[str] = field(default_factory=set)
    vulnerable: Set[str] = field(default_factory=set)
    immune: Set[str] = field(default_factory=set)
    temp_hp: int = 0
    consumables: Dict[str, int] = field(default_factory=dict)  # e.g., {"Potion of Healing": 2}
    death: DeathState = field(default_factory=DeathState)  # per-combat state
    concentration: Optional[str] = None  # name/label of the effect or spell

    def __post_init__(self) -> None:
        if self.max_hp is None:
            self.max_hp = self.hp
