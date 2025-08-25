import random
from dataclasses import dataclass


@dataclass
class RNG:
    seed: int

    def __post_init__(self) -> None:
        self._r = random.Random(self.seed)

    def roll_int(self, lo: int, hi: int) -> int:
        return self._r.randint(lo, hi)

    def roll(self, dice: str) -> int:
        # naive parser for 'XdY+Z'
        total = 0
        expr = dice.lower().replace(" ", "")
        if "+" in expr:
            dice_part, mod_part = expr.split("+", 1)
            mod = int(mod_part)
        else:
            dice_part, mod = expr, 0
        count, sides = dice_part.split("d", 1)
        for _ in range(int(count)):
            total += self.roll_int(1, int(sides))
        return total + mod
