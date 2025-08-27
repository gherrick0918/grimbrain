from pathlib import Path

from grimbrain.characters import PCOptions, create_pc
from grimbrain.sheet_pdf import save_pdf


def test_pdf_written(tmp_path: Path):
    pc = create_pc(
        PCOptions(
            name="Elora",
            klass="Wizard",
            race="High Elf",
            background="Sage",
            ac=12,
            abilities={"str": 8, "dex": 14, "con": 12, "int": 16, "wis": 10, "cha": 12},
        )
    )
    p = tmp_path / "elora.pdf"
    save_pdf(pc, p)
    assert p.exists() and p.stat().st_size > 1000

