from grimbrain.models import MonsterSidecar
from grimbrain.engine.encounter import compute_encounter

def goblin():
    return MonsterSidecar(
        name="Goblin",
        source="MM",
        ac="15",
        hp="7",
        speed="30 ft.",
        str=8,
        dex=14,
        con=10,
        int=10,
        wis=8,
        cha=8,
        traits=[],
        actions=[],
        reactions=[],
        provenance=[],
    )


def test_one_goblin():
    res = compute_encounter([goblin()])
    assert res["total_xp"] == 50
    assert res["adjusted_xp"] == 50
    assert res["band"] == "1"


def test_three_goblins():
    g = goblin()
    res = compute_encounter([g, g, g])
    assert res["total_xp"] == 150
    assert res["adjusted_xp"] == 300
    assert res["band"] == "3-6"
