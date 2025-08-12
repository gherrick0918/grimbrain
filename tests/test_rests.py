import random

from grimbrain.engine import rests
from grimbrain.models import PC


def test_short_rest_heals(tmp_path):
    pc = PC(name="Hero", ac=10, hp=5, max_hp=10, con_mod=2, attacks=[])
    rng = random.Random(1)
    deltas = rests.apply_short_rest([pc], rng)
    assert 0 < deltas["Hero"] <= 10
    assert pc.hp <= pc.max_hp


def test_long_rest_full_heal():
    pc = PC(name="Hero", ac=10, hp=3, max_hp=10, attacks=[])
    deltas = rests.apply_long_rest([pc])
    assert deltas["Hero"] == 7
    assert pc.hp == 10
