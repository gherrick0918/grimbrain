from grimbrain.engine.damage import apply_defenses
from grimbrain.engine.types import Combatant


def T(res=None, vul=None, imm=None, thp=0):
    return Combatant(name="T", actor=object(), hp=10, weapon="Mace",
                     resist=set(res or []), vulnerable=set(vul or []),
                     immune=set(imm or []), temp_hp=thp)


def test_resistance_halves_and_rounds_down_before_thp():
    d = T(res={"slashing"}, thp=3)
    final, notes, spent = apply_defenses(9, "slashing", d)  # 9 -> 4 -> THP 3 -> 1
    assert final == 1 and spent == 3
    assert any("halved" in n for n in notes)


def test_vulnerability_doubles():
    d = T(vul={"bludgeoning"})
    final, _, _ = apply_defenses(5, "bludgeoning", d)  # 5 -> 10
    assert final == 10


def test_immunity_zeroes_damage():
    d = T(imm={"piercing"}, thp=5)
    final, notes, spent = apply_defenses(12, "piercing", d)
    assert final == 0 and spent == 0
    assert any("immune" in n for n in notes)


def test_temp_hp_only_soaks_remaining():
    d = T(thp=2)
    final, _, spent = apply_defenses(1, "acid", d)  # 1 -> THP 1 -> 0; leaves 1 THP
    assert final == 0 and d.temp_hp == 1 and spent == 1
