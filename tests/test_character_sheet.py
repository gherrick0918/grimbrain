import json
from pathlib import Path

from grimbrain.models_character import (
    PCSheet,
    ability_mod,
    attack_to_hit,
    load_pc_sheet,
    spell_save_dc,
)


def test_load_sheet_and_helpers(tmp_path):
    data = {
        "name": "Brynn",
        "class": "Wizard",
        "level": 3,
        "abilities": {"str": 8, "dex": 14, "con": 12, "int": 16, "wis": 12, "cha": 10},
        "ac": 14,
        "hp": 16,
        "attacks": [
            {
                "name": "Quarterstaff",
                "proficient": True,
                "ability": "str",
                "damage_dice": "1d6+2",
                "type": "melee",
            }
        ],
        "prepared_spells": [{"name": "Fireball", "level": 3}],
        "resources": {"hit_dice": "3d6"},
    }
    path = tmp_path / "pc_wizard.json"
    path.write_text(json.dumps(data))
    sheet = load_pc_sheet(path)
    assert ability_mod(sheet.abilities["int"]) == 3
    assert sheet.pb == 2
    assert spell_save_dc(sheet) == 13
    atk = sheet.attacks[0]
    assert attack_to_hit(sheet, atk) == 1
    pc = sheet.to_pc()
    assert pc.attacks[0].to_hit == 1
