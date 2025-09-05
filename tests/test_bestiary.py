from grimbrain.engine.bestiary import make_combatant_from_monster, weapon_names_for_monster


def test_load_goblin_minimal_fields():
    c = make_combatant_from_monster("Goblin", team="A", cid="G")
    assert c.name == "Goblin" and c.ac > 0 and c.max_hp == c.hp
    assert isinstance(c.str_mod, int) and isinstance(c.dex_mod, int)


def test_weapon_mapping_exists():
    w1, w2 = weapon_names_for_monster("Goblin")
    assert w1 is not None
