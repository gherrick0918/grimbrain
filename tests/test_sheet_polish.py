from pathlib import Path

import pytest

from grimbrain.characters import PCOptions, create_pc
from grimbrain.sheet import to_markdown

try:
    from grimbrain.sheet_pdf import save_pdf
except ModuleNotFoundError:  # pragma: no cover - optional dep
    save_pdf = None


def _pc():
    return create_pc(
        PCOptions(
            name="Elora",
            klass="Wizard",
            race="High Elf",
            background="Sage",
            ac=12,
            abilities={"str": 8, "dex": 14, "con": 12, "int": 16, "wis": 10, "cha": 12},
        )
    )


def test_md_footer_and_caps(tmp_path: Path):
    md = to_markdown(
        _pc(), meta={"campaign": "Starter", "seed": "1"}, show_zero_slots=True
    )
    assert "INT, WIS" in md
    assert "L2:0" in md and "SLOTS" in md.upper()
    assert "CAMPAIGN: Starter" in md and "SEED: 1" in md


def test_pdf_footer(tmp_path: Path):
    pytest.importorskip("reportlab")
    assert save_pdf is not None
    p = tmp_path / "elora_polished.pdf"
    save_pdf(_pc(), p, meta={"campaign": "Starter", "seed": "1"}, show_zero_slots=True)
    assert p.exists() and p.stat().st_size > 1000
