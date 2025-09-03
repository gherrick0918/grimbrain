from dataclasses import dataclass
from typing import Dict, Optional
from pathlib import Path
import json


@dataclass(frozen=True)
class Armor:
    name: str
    category: str          # light | medium | heavy | shield
    base_ac: int           # armor’s base (0 for shield)
    dex_cap: Optional[int] # None=no cap; 2=medium; 0=heavy (ignore Dex)
    stealth_disadvantage: bool
    str_min: Optional[int]


class ArmorIndex:
    def __init__(self, by_name: Dict[str, Armor]):
        self.by_name = by_name

    @classmethod
    def load(cls, path: Path) -> "ArmorIndex":
        raw = json.loads(path.read_text(encoding="utf-8"))
        by_name = {}
        for a in raw:
            ar = Armor(**a)
            by_name[ar.name.lower()] = ar
        return cls(by_name)

    def get(self, name: str) -> Armor:
        return self.by_name[name.lower()]
