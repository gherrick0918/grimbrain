from engine.combat import run_round
from models import ActionStruct, MonsterSidecar, PC, Attack


def make_goblin():
    return MonsterSidecar(
        name="Goblin",
        source="MM",
        ac="15",
        hp="7",
        speed="30 ft",
        str=8,
        dex=14,
        con=10,
        int=10,
        wis=8,
        cha=8,
        traits=[],
        actions=[],
        actions_struct=[
            ActionStruct(
                name="Scimitar",
                attack_bonus=4,
                type="melee",
                reach_or_range="5 ft",
                target="one target",
                hit_text="",
                damage_dice="1d6+2",
                damage_type="slashing",
            )
        ],
        reactions=[],
        provenance=[],
    )


def make_goblin_boss():
    return MonsterSidecar(
        name="Goblin Boss",
        source="MM",
        ac="17",
        hp="21",
        speed="30 ft",
        str=10,
        dex=14,
        con=12,
        int=10,
        wis=10,
        cha=10,
        traits=[],
        actions=[],
        actions_struct=[
            ActionStruct(
                name="Scimitar",
                attack_bonus=4,
                type="melee",
                reach_or_range="5 ft",
                target="one target",
                hit_text="",
                damage_dice="1d6+2",
                damage_type="slashing",
            )
        ],
        reactions=[],
        provenance=[],
    )


def make_pc(name="Hero"):
    return PC(
        name=name,
        ac=15,
        hp=20,
        attacks=[Attack(name="Sword", to_hit=5, damage_dice="1d8+3", type="melee")],
    )


def test_pc_vs_goblin_round():
    pc = make_pc()
    goblin = make_goblin()
    result = run_round([pc], [goblin], seed=1)
    party = result["state"]["party"][0]
    monster = result["state"]["monsters"][0]
    assert party["hp"] == 15 and not party["defeated"]
    assert monster["hp"] == 7 and not monster["defeated"]


def test_two_pcs_vs_boss():
    pcs = [make_pc("Hero1"), make_pc("Hero2")]
    boss = make_goblin_boss()
    result = run_round(pcs, [boss], seed=2)
    boss_state = result["state"]["monsters"][0]
    assert boss_state["hp"] == 13 and not boss_state["defeated"]
    party_hps = [p["hp"] for p in result["state"]["party"]]
    assert party_hps == [20, 20]
