from grimbrain.characters import PCOptions, add_item, create_pc, learn_spell, level_up


def test_create_and_level():
    opts = PCOptions(
        name="Elora",
        klass="Wizard",
        race="High Elf",
        background="Sage",
        ac=12,
        abilities={"str": 8, "dex": 14, "con": 12, "int": 16, "wis": 10, "cha": 12},
    )
    pc = create_pc(opts)
    assert pc.max_hp >= 6 + ((12 - 10) // 2)  # d6 + CON mod
    assert pc.prof == 2

    pc2 = level_up(pc, 3)
    assert pc2.level == 3
    assert pc2.spell_slots is not None and pc2.spell_slots.l2 >= 0

    add_item(pc2, "Potion of Healing", 1)
    learn_spell(pc2, "Magic Missile")
    assert any(i.name == "Potion of Healing" for i in pc2.inventory)
    assert "Magic Missile" in pc2.spells
