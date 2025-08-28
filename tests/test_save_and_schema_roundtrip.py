from pathlib import Path

from grimbrain.characters import PCOptions, create_pc, save_pc
from grimbrain.validation import load_pc


def test_roundtrip_pc_json(tmp_path: Path) -> None:
    p = tmp_path / "pc.json"
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
    # has prof sets internally; save should serialize lists & omit Nones
    save_pc(pc, p)
    # load must pass JSON Schema and pydantic parsing
    pc2 = load_pc(p)
    assert pc2.name == "Elora" and pc2.class_ == "Wizard"
