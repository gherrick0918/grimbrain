from dataclasses import dataclass
from typing import Optional, Literal

Cover = Literal["none", "half", "three-quarters", "total"]


@dataclass
class Target:
    ac: int
    hp: int
    cover: Cover = "none"
    distance_ft: Optional[int] = None
