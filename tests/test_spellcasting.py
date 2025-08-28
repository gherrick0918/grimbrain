from pathlib import Path
import pytest
from grimbrain.characters import PCOptions, create_pc, save_pc, load_pc
from grimbrain.characters import learn_spell, prepare_spell, cast_slot, long_rest
from grimbrain.characters import spell_save_dc, spell_attack_bonus


def _wiz():
    return PCOptions(
        name="Elora", class_="Wizard", race="High Elf", background="Sage", ac=12,
        abilities={"str":8,"dex":14,"con":12,"int":16,"wis":10,"cha":12}
    )

def test_dc_and_attack_bonus():
    pc = create_pc(_wiz())
    assert spell_save_dc(pc) == 8 + pc.prof + pc.ability_mod("int")
    assert spell_attack_bonus(pc) == pc.prof + pc.ability_mod("int")

def test_learn_prepare_and_cast(tmp_path: Path):
    pc = create_pc(_wiz())
    learn_spell(pc, "Magic Missile")
    prepare_spell(pc, "Magic Missile")  # Wizard allowed
    # Give some slots
    assert pc.spell_slots and pc.spell_slots.l1 >= 2
    before = pc.spell_slots.l1
    cast_slot(pc, 1)
    assert pc.spell_slots.l1 == before - 1
    long_rest(pc)
    assert pc.spell_slots.l1 >= 2  # restored

def test_prepare_unknown_raises():
    pc = create_pc(_wiz())
    with pytest.raises(ValueError):
        prepare_spell(pc, "Shield")  # not learned
