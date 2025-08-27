from __future__ import annotations
from dataclasses import dataclass

STANDARD_ARRAY = (15, 14, 13, 12, 10, 8)
COSTS = {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}  # 27-point buy


@dataclass
class PointBuy:
    str: int
    dex: int
    con: int
    int: int
    wis: int
    cha: int

    @property
    def cost(self) -> int:
        return sum(COSTS[v] for v in (self.str, self.dex, self.con, self.int, self.wis, self.cha))

    def as_dict(self) -> dict:
        return {
            "str": self.str,
            "dex": self.dex,
            "con": self.con,
            "int": self.int,
            "wis": self.wis,
            "cha": self.cha,
        }
