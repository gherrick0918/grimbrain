from grimbrain.engine.encounter import apply_difficulty
from grimbrain.fallback_monsters import FALLBACK_MONSTERS
from grimbrain.models import MonsterSidecar


def _mon():
    return MonsterSidecar(**FALLBACK_MONSTERS["goblin"])


def test_difficulty_hp_changes():
    m_easy = _mon()
    m_hard = _mon()
    apply_difficulty([m_easy], "easy", False, 2)
    apply_difficulty([m_hard], "hard", False, 2)
    assert int(m_easy.hp) < int(m_hard.hp)


def test_scaling_party_size():
    m_small = _mon()
    m_large = _mon()
    apply_difficulty([m_small], "normal", True, 2)
    apply_difficulty([m_large], "normal", True, 5)
    assert int(m_small.hp) < int(m_large.hp)
