from pathlib import Path

from pathlib import Path

from grimbrain.characters import PCOptions, create_pc, apply_starter_kits


def _wiz_opts():
    return PCOptions(
        name="Elora",
        class_="Wizard",
        race="High Elf",
        background="Sage",
        ac=12,
        abilities={"str": 8, "dex": 14, "con": 12, "int": 16, "wis": 10, "cha": 12},
    )


def test_starter_kits_add_items_and_langs_tools(tmp_path: Path):
    pc = create_pc(_wiz_opts())
    apply_starter_kits(pc)
    names = {i.name for i in pc.inventory}
    assert "Quarterstaff" in names and "Spellbook" in names
    # from background
    assert any("Parchment" in i.name for i in pc.inventory)
    # languages/tools present (Sage has a flex 'Any'; just ensure recorded)
    assert len(pc.languages) >= 1
    # Doesn't crash if re-applied (idempotent-ish for simple lists)
    apply_starter_kits(pc)


def test_cli_equip_unknown_preset_raises(tmp_path: Path, monkeypatch):
    # Minimal PC file
    from grimbrain.characters import save_pc

    pc = create_pc(_wiz_opts())
    p = tmp_path / "pc.json"
    save_pc(pc, p)
    import subprocess, sys

    cp = subprocess.run(
        [
            sys.executable,
            "-m",
            "grimbrain",
            "character",
            "equip",
            str(p),
            "--preset",
            "Nope",
        ],
        capture_output=True,
        text=True,
    )
    assert cp.returncode != 0
