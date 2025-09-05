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
    team: str = "A"     # e.g., "A", "B"
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
    attacks_per_action: int = 1  # <-- Add this line
    reaction_available: bool = True  # reset at start of each round
    grappled_by: Optional[str] = None
    proficient_athletics: bool = False
    proficient_acrobatics: bool = False
    # --- PR40 short-lived tactical state ---
    dodging: bool = False
    help_tokens: Dict[str, int] = field(default_factory=dict)  # target_id -> remaining uses
    readied_action: Optional["Readied"] = None
    id: Optional[str] = None  # simple identifier for mapping help/ready triggers

    def __post_init__(self) -> None:
        if self.max_hp is None:
            self.max_hp = self.hp
        if self.id is None:
            # default identifier: use name
            self.id = self.name

    def clear_grapple(self) -> None:
        self.conditions.discard("grappled")
        self.grappled_by = None

    # --- PR40 helpers ---
    def consume_help_token(self, target_id: str) -> bool:
        """Decrement and remove a help token against ``target_id`` if present."""
        n = self.help_tokens.get(target_id, 0)
        if n > 0:
            new_n = n - 1
            if new_n > 0:
                self.help_tokens[target_id] = new_n
            else:
                self.help_tokens.pop(target_id, None)
            return True
        return False


@dataclass
class Readied:
    """Simplified readied attack descriptor."""
    trigger: str  # e.g. "enemy_enters_melee" | "enemy_within_30ft"
    target_id: str
    weapon_name: Optional[str] = None
