from pathlib import Path

from grimbrain.codex.weapons import WeaponIndex
from grimbrain.character import Character


def idx():
    return WeaponIndex.load(Path("data/weapons.json"))


def test_ammo_inference_and_display():
    i = idx()
    c = Character(dex_score=16, proficiencies={"simple weapons", "martial weapons"})
    c.equipped_weapons = ["Shortbow", "Hand Crossbow", "Blowgun"]
    c.ammo = {"arrows": 20, "bolts": 12, "needles": 5}

    block = c.attacks_and_spellcasting(i)
    props = {e["name"]: e["properties"] for e in block}
    assert "arrows: 20" in props["Shortbow"]
    assert "bolts: 12" in props["Hand Crossbow"]
    assert "needles: 5" in props["Blowgun"]


def test_spend_ammo_success_and_failure():
    c = Character()
    c.add_ammo("arrows", 2)
    assert c.ammo_count("arrows") == 2
    assert c.spend_ammo("arrows", 1) is True
    assert c.ammo_count("arrows") == 1
    assert c.spend_ammo("arrows", 2) is False  # not enough
    assert c.ammo_count("arrows") == 1


def test_explicit_ammo_override():
    i = idx()
    w = i.get("Longbow")
    assert w.ammo_type() == "arrows"
