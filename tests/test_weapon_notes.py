from pathlib import Path
from grimbrain.codex.weapons import WeaponIndex
from grimbrain.rules.weapon_notes import weapon_notes

def idx():
    return WeaponIndex.load(Path("data/weapons.json"))

def test_lance_notes_present():
    i = idx()
    w = i.get("lance")
    notes = " ".join(weapon_notes(w)).lower()
    assert "disadvantage" in notes and "5 ft" in notes and "two-handed" in notes

def test_net_notes_present():
    i = idx()
    w = i.get("net")
    notes = " ".join(weapon_notes(w)).lower()
    assert "restrained" in notes and "str dc 10" in notes and "ac 10" in notes

def test_loading_note_on_crossbow():
    i = idx()
    w = i.get("light crossbow")
    notes = " ".join(weapon_notes(w)).lower()
    assert "loading" in notes and "one shot" in notes
