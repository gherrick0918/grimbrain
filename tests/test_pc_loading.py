import json
from pathlib import Path

from engine.combat import run_round
from models import PC, ActionStruct, MonsterSidecar


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


def test_load_two_pcs_and_round():
    path = Path(__file__).parent / "pc.json"
    pcs_data = json.loads(path.read_text())
    pcs = [PC(**d) for d in pcs_data]
    goblin = make_goblin()
    result = run_round(pcs, [goblin], seed=1)
    monster = result["state"]["monsters"][0]
    assert monster["hp"] == 3 and not monster["defeated"]
    assert len(result["state"]["party"]) == 2
