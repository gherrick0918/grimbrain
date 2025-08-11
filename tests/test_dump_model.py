from grimbrain.models import PC, Attack, dump_model


def test_dump_model_returns_dict():
    pc = PC(name="Test", ac=10, hp=5, attacks=[Attack(name="hit", damage_dice="1d4", type="melee")])
    attack_dict = dump_model(pc.attacks[0])
    assert isinstance(attack_dict, dict)
    assert attack_dict["name"] == "hit"
