import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from grimbrain.engine.characters import (
    build_partymember,
    roll_abilities,
    scores_from_list_desc,
)


def test_roll_abilities_deterministic():
    a = roll_abilities(seed=1234)
    b = roll_abilities(seed=1234)
    c = roll_abilities(seed=1235)
    assert a == b
    assert a != c
    assert len(a) == 6 and all(3 <= v <= 18 for v in a)


def test_build_from_rolled_scores():
    scores = scores_from_list_desc([17, 15, 14, 12, 10, 8])
    pm = build_partymember("Test", "Fighter", scores, "Longsword", False)
    assert pm.name == "Test"
    # AC: 10 + Dex mod (from 15 = +2)
    assert pm.ac == 12
    # HP: d10 + Con mod (from 14 = +2)
    assert pm.max_hp == 12
