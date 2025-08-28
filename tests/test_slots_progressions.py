from grimbrain.characters import PCOptions, create_pc, level_up


def _opts(class_, subclass=None):
    return PCOptions(
        name="Test", class_=class_, subclass=subclass, race=None, background=None, ac=12,
        abilities={"str":10,"dex":10,"con":10,"int":10,"wis":10,"cha":10}
    )


def test_paladin_half_caster():
    pc = create_pc(_opts("Paladin"))
    assert pc.spell_slots is None  # L1 no slots
    pc = level_up(pc, 2)
    assert pc.spell_slots and pc.spell_slots.l1 == 2
    pc = level_up(pc, 5)
    assert pc.spell_slots.l2 >= 1  # gains 2nd-level slots by 5


def test_ranger_half_caster():
    pc = create_pc(_opts("Ranger"))
    assert pc.spell_slots is None
    pc = level_up(pc, 3)
    assert pc.spell_slots and pc.spell_slots.l1 >= 3


def test_eldritch_knight_third_caster():
    pc = create_pc(_opts("Fighter", "Eldritch Knight"))
    assert pc.spell_slots is None  # L1, no subclass yet
    pc = level_up(pc, 3)
    assert pc.spell_slots and pc.spell_slots.l1 == 2
    pc = level_up(pc, 7)
    assert pc.spell_slots.l2 >= 2


def test_arcane_trickster_third_caster():
    pc = create_pc(_opts("Rogue", "Arcane Trickster"))
    pc = level_up(pc, 3)
    assert pc.spell_slots and pc.spell_slots.l1 >= 2
