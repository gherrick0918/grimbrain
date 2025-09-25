import random

from grimbrain.engine.characters import build_partymember
from grimbrain.engine.types import roll_d20


class SequenceRandom(random.Random):
    def __init__(self, sequence):
        super().__init__()
        self._sequence = list(sequence)

    def randint(self, a, b):  # noqa: D401 - deterministic sequence helper
        return self._sequence.pop(0)


def test_halfling_lucky_rerolls_one():
    pm = build_partymember(
        name="Hal",
        cls="Rogue",
        scores={"STR": 8, "DEX": 14, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10},
        weapon="Shortbow",
        ranged=True,
        features={"lucky": True},
    )
    rng = SequenceRandom([1, 7])
    notes: list[str] = []
    result = roll_d20(rng, pm=pm, log=notes)
    assert result == 7
    assert notes and "lucky" in notes[0]


def test_roll_d20_without_lucky_keeps_one():
    pm = build_partymember(
        name="NoLuck",
        cls="Fighter",
        scores={"STR": 15, "DEX": 10, "CON": 14, "INT": 10, "WIS": 10, "CHA": 8},
        weapon="Longsword",
        ranged=False,
    )
    rng = SequenceRandom([1])
    result = roll_d20(rng, pm=pm)
    assert result == 1
