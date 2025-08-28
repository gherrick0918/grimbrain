from pathlib import Path

from grimbrain.characters import PCOptions, create_pc
from grimbrain.sheet import to_markdown


def test_sheet_md_contains_core_fields(tmp_path: Path):
    pc = create_pc(
        PCOptions(
            name="Elora",
            class_="Wizard",
            race="High Elf",
            background="Sage",
            ac=12,
            abilities={"str": 8, "dex": 14, "con": 12, "int": 16, "wis": 10, "cha": 12},
        )
    )
    pc.weapon_proficiencies.add("simple weapons")
    pc.equipped_weapons.append("Dagger")
    md = to_markdown(pc)
    assert "# Elora" in md
    assert "**Class:** Wizard" in md
    assert "## Abilities" in md and "**INT**" in md
    assert "## Proficiencies" in md and "Proficiency Bonus" in md
    assert "## Attacks & Spellcasting" in md
    assert "## Spellcasting" in md
