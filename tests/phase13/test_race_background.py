from grimbrain.engine.characters import (
    ABILS,
    apply_asi,
    build_partymember,
    load_pc,
    save_pc,
)


def test_apply_asi_human_all_plus_one():
    base = {ability: 10 for ability in ABILS}
    asi = [{"ability": ability, "bonus": 1} for ability in ABILS]
    updated = apply_asi(base, asi)
    assert all(updated[ability] == 11 for ability in ABILS)


def test_build_with_elf_sage_merges_profs_and_scores():
    scores = {"STR": 10, "DEX": 16, "CON": 10, "INT": 12, "WIS": 10, "CHA": 8}
    pm = build_partymember(
        name="Nyra",
        cls="Wizard",
        scores=scores,
        weapon="Dagger",
        ranged=False,
        prof_skills=["Arcana", "History", "Perception"],
        race="Elf",
        background="Sage",
        languages=["Common", "Elvish"],
        tool_profs=[],
    )
    assert pm.ac == 13
    assert set(pm.prof_skills) == {"Arcana", "History", "Perception"}
    assert pm.race == "Elf"
    assert pm.background == "Sage"
    assert pm.languages == ["Common", "Elvish"]


def test_party_member_round_trip_preserves_new_fields(tmp_path):
    scores = {"STR": 10, "DEX": 12, "CON": 10, "INT": 14, "WIS": 11, "CHA": 9}
    pm = build_partymember(
        name="Archivist",
        cls="Wizard",
        scores=scores,
        weapon="Quarterstaff",
        ranged=False,
        prof_skills=["Arcana", "History"],
        prof_saves=["Wisdom"],
        race="Human",
        background="Sage",
        languages=["Common", "Draconic"],
        tool_profs=["Calligrapher's Supplies"],
    )
    path = tmp_path / "pc.json"
    save_pc(pm, path.as_posix())
    loaded = load_pc(path.as_posix())
    assert loaded.race == "Human"
    assert loaded.background == "Sage"
    assert loaded.languages == ["Common", "Draconic"]
    assert loaded.tool_profs == ["Calligrapher's Supplies"]
