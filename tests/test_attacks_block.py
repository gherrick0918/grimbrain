import os
from pathlib import Path
from grimbrain.characters import PCOptions, create_pc
from grimbrain.sheet import to_markdown


def extract_block(md: str) -> str:
    lines = []
    in_block = False
    for line in md.splitlines():
        if line.startswith("## Attacks & Spellcasting"):
            in_block = True
            continue
        if in_block and line.startswith("## "):
            break
        if in_block:
            lines.append(line)
    return "\n".join(l for l in lines if l).strip() + "\n"


def test_attacks_block_golden():
    pc = create_pc(
        PCOptions(
            name="Aragorn",
            class_="Fighter",
            race="Human",
            background=None,
            ac=16,
            abilities={"str": 16, "dex": 14, "con": 14, "int": 10, "wis": 12, "cha": 12},
        )
    )
    pc.weapon_proficiencies = {"martial weapons", "simple weapons"}
    pc.equipped_weapons = ["Longsword", "Dagger"]
    md = to_markdown(pc)
    got = extract_block(md)
    golden = Path("tests/golden/attacks_block.golden")
    if os.environ.get("UPDATE_GOLDEN"):
        golden.write_text(got, encoding="utf-8")
    want = golden.read_text(encoding="utf-8")
    assert got == want
