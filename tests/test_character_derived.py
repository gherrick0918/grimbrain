from grimbrain.characters import PCOptions, create_pc


def _wiz():
    return PCOptions(
        name="Elora",
        class_="Wizard",
        race="High Elf",
        background="Sage",
        ac=12,
        abilities={"str": 8, "dex": 14, "con": 12, "int": 16, "wis": 10, "cha": 12},
    )


def test_saves_and_skills():
    pc = create_pc(_wiz())
    # Sage adds arcana/history; Wizard saves int/wis
    assert pc.save_proficiencies == {"int", "wis"}
    assert {"arcana", "history"}.issubset(pc.skill_proficiencies)
    # Passive Perception baseline
    assert pc.passive_perception >= 10


def test_spell_slots_tables():
    from grimbrain.characters import level_up

    pc = create_pc(_wiz())
    pc = level_up(pc, 5)
    assert pc.spell_slots and pc.spell_slots.l3 >= 2
