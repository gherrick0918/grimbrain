from dataclasses import dataclass
from typing import List, Dict, Optional
import json
import re
from pathlib import Path

# Allowed weapon property keys
_ALLOWED_PROP_KEYS = {
    "finesse",
    "light",
    "heavy",
    "two-handed",
    "reach",
    "loading",
    "ammunition",
    "thrown",
    "special",
    "range",
    "versatile",
    "ammo",
}

# Recognised ammunition types for explicit overrides
_ALLOWED_AMMO_TYPES = {"arrows", "bolts", "stones", "needles"}

_VERSATILE_VAL_PAT = re.compile(r"^\d+d\d+$")


def _range_ok(val: str) -> bool:
    try:
        a, b = (int(x) for x in val.split("/", 1))
    except Exception:
        return False
    return a > 0 and b >= a


def _validate_weapon_dict(w: dict) -> list[str]:
    errs: list[str] = []
    name = w.get("name", "<unnamed>")
    for p in w.get("properties", []):
        key, val = (p.split(":", 1) + [None])[:2]
        if key not in _ALLOWED_PROP_KEYS:
            errs.append(f"{name}: unknown property '{key}'")
            continue
        if key == "range" and not (val and _range_ok(val)):
            errs.append(f"{name}: bad range '{p}', expected range:X/Y")
        if key == "versatile" and not (val and _VERSATILE_VAL_PAT.match(val)):
            errs.append(f"{name}: bad versatile '{p}', expected versatile:XdY")
        if key == "ammo" and val not in _ALLOWED_AMMO_TYPES:
            errs.append(
                f"{name}: bad ammo '{p}', expected one of {sorted(_ALLOWED_AMMO_TYPES)}"
            )
    return errs

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

    def ammo_type(self) -> Optional[str]:
        """Return the ammunition type for this weapon, if any."""
        if not self.has_prop("ammunition"):
            return None
        explicit = self.get_prop_value("ammo")
        if explicit:
            return explicit
        n = self.name.lower()
        if "bow" in n and "cross" not in n:
            return "arrows"
        if "crossbow" in n:
            return "bolts"
        if "sling" in n:
            return "stones"
        if "blowgun" in n:
            return "needles"
        return None


class WeaponIndex:
    def __init__(self, weapons: Dict[str, Weapon]):
        self.by_name = weapons

    @classmethod
    def load(cls, path: Path) -> "WeaponIndex":
        raw = json.loads(path.read_text(encoding="utf-8"))
        weapons = {}
        errors: list[str] = []
        for w in raw:
            errors.extend(_validate_weapon_dict(w))
            weapon = Weapon(**w)
            weapons[weapon.name.lower()] = weapon
        if errors:
            raise ValueError("; ".join(errors))
        return cls(weapons)

    def get(self, name: str) -> Weapon:
        return self.by_name[name.lower()]
