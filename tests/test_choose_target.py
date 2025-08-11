from grimbrain.engine.combat import Combatant, choose_target


def make_enemy(name, hp):
    return Combatant(name, ac=10, hp=hp, attacks=[], side="monsters")


def test_lowest_hp():
    actor = Combatant("hero", 10, 10, [], "party")
    enemies = [make_enemy("e1", 5), make_enemy("e2", 3), make_enemy("e3", 8)]
    target = choose_target(actor, enemies, strategy="lowest_hp")
    assert target.name == "e2"


def test_random_seeded():
    actor = Combatant("hero", 10, 10, [], "party")
    enemies = [make_enemy("e1", 5), make_enemy("e2", 3)]
    t1 = choose_target(actor, enemies, strategy="random", seed=1)
    t2 = choose_target(actor, enemies, strategy="random", seed=1)
    assert t1.name == t2.name
