from dataclasses import dataclass
from typing import List, Dict, Optional
import json
import re
from pathlib import Path

@dataclass(frozen=True)
class Weapon:
    name: str
    category: str           # "simple" | "martial"
    kind: str               # "melee" | "ranged"
    damage: str             # "1d6" etc.
    damage_type: str        # "slashing" | "piercing" | "bludgeoning"
    properties: List[str]   # e.g., ["finesse", "versatile:1d10", "range:20/60"]

    def has_prop(self, key: str) -> bool:
        return any(p.split(":")[0] == key for p in self.properties)

    def get_prop_value(self, key: str) -> Optional[str]:
        for p in self.properties:
            k, *rest = p.split(":")
            if k == key and rest:
                return rest[0]
        return None

    def versatile_die(self) -> Optional[str]:
        return self.get_prop_value("versatile")

    def range_tuple(self) -> Optional[tuple]:
        val = self.get_prop_value("range")
        if not val:
            return None
        m = re.match(r"(\d+)\/(\d+)", val)
        return (int(m.group(1)), int(m.group(2))) if m else None


class WeaponIndex:
    def __init__(self, weapons: Dict[str, Weapon]):
        self.by_name = weapons

    @classmethod
    def load(cls, path: Path) -> "WeaponIndex":
        raw = json.loads(path.read_text(encoding="utf-8"))
        weapons = {}
        for w in raw:
            weapon = Weapon(**w)
            weapons[weapon.name.lower()] = weapon
        return cls(weapons)

    def get(self, name: str) -> Weapon:
        return self.by_name[name.lower()]
