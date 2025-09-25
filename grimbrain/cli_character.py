from __future__ import annotations

from pathlib import Path

import typer

from grimbrain.characters import (
    PCOptions,
    add_item,
    apply_starter_kits,
    create_pc,
    level_up,
    save_pc,
    load_pc,
    PrettyError,
    learn_spell,
    prepare_spell,
    unprepare_spell,
    spell_save_dc,
    spell_attack_bonus,
    cast_slot,
    long_rest,
    short_rest,
)
from grimbrain.sheet import render_console, save_markdown
from grimbrain.sheet_pdf import save_pdf
from grimbrain.rules_equipment import CLASS_KITS, BACKGROUND_KITS

char_app = typer.Typer(help="Character creation and management")


@char_app.command("create")
def create(
    name: str = typer.Option(...),
    class_: str = typer.Option(..., "--class", help="Class, e.g. Wizard"),
    subclass: str = typer.Option(None, help="Subclass (for EK/AT etc.)"),
    race: str = typer.Option(None),
    background: str = typer.Option(None),
    ac: int = typer.Option(12),
    str_: int = typer.Option(8, "--str"),
    dex: int = typer.Option(8, "--dex"),
    con: int = typer.Option(8, "--con"),
    int_: int = typer.Option(8, "--int"),
    wis: int = typer.Option(8, "--wis"),
    cha: int = typer.Option(8, "--cha"),
    out: Path = typer.Option(Path("pc.json"), help="Output file"),
    starter: bool = typer.Option(
        False, help="Apply class/background equipment & prof packs"
    ),
):
    opts = PCOptions(
        name=name,
        class_=class_,
        subclass=subclass,
        race=race,
        background=background,
        ac=ac,
        abilities={
            "str": str_,
            "dex": dex,
            "con": con,
            "int": int_,
            "wis": wis,
            "cha": cha,
        },
    )
    pc = create_pc(opts)
    if starter:
        apply_starter_kits(pc)
    save_pc(pc, out)
    typer.secho(f"Created PC → {out}", fg=typer.colors.GREEN)


@char_app.command("array")
def make_from_array(
    name: str = typer.Option(...),
    class_: str = typer.Option(..., "--class"),
    subclass: str = typer.Option(None, help="Subclass"),
    race: str = typer.Option(None),
    background: str = typer.Option(None),
    ac: int = typer.Option(12),
    arr: str = typer.Option(
        "15,14,13,12,10,8", help="Comma-sep standard array (high->low)"
    ),
    assign: str = typer.Option(
        "int,dex,con,str,wis,cha", help="Order to assign stats (comma sep)"
    ),
    out: Path = typer.Option(Path("pc.json")),
    starter: bool = typer.Option(
        False, help="Apply class/background starter packs"
    ),
):
    vals = [int(x) for x in arr.split(",")]
    keys = assign.split(",")
    abilities = dict(zip(keys, vals))
    opts = PCOptions(
        name=name,
        class_=class_,
        subclass=subclass,
        race=race,
        background=background,
        ac=ac,
        abilities=abilities,
    )
    pc = create_pc(opts)
    if starter:
        apply_starter_kits(pc)
    save_pc(pc, out)
    typer.secho(f"Created PC from array → {out}", fg=typer.colors.GREEN)


@char_app.command("pointbuy")
def make_from_pointbuy(
    name: str = typer.Option(...),
    class_: str = typer.Option(..., "--class"),
    subclass: str = typer.Option(None, help="Subclass"),
    race: str = typer.Option(None),
    background: str = typer.Option(None),
    ac: int = typer.Option(12),
    stats: str = typer.Option("15,14,13,12,10,8"),
    out: Path = typer.Option(Path("pc.json")),
    starter: bool = typer.Option(
        False, help="Apply class/background starter packs"
    ),
):
    vals = [int(x) for x in stats.split(",")]
    abilities = {k: v for k, v in zip(["str", "dex", "con", "int", "wis", "cha"], vals)}
    from grimbrain.pointbuy import PointBuy

    pb = PointBuy(**abilities)
    if pb.cost > 27:
        raise typer.BadParameter(f"Point-buy total {pb.cost} exceeds 27")
    opts = PCOptions(
        name=name,
        class_=class_,
        subclass=subclass,
        race=race,
        background=background,
        ac=ac,
        abilities=pb.as_dict(),
    )
    pc = create_pc(opts)
    if starter:
        apply_starter_kits(pc)
    save_pc(pc, out)
    typer.secho(
        f"Created PC via point-buy (cost={pb.cost}) → {out}",
        fg=typer.colors.GREEN,
    )


@char_app.command("level")
def level(
    file: Path = typer.Argument(..., exists=True),
    to: int = typer.Option(..., help="New level"),
):
    try:
        pc = load_pc(file)
    except PrettyError as e:
        raise typer.Exit(code=1) from e
    pc = level_up(pc, to)
    save_pc(pc, file)
    typer.secho(f"Leveled {pc.name} to {pc.level}", fg=typer.colors.GREEN)


@char_app.command("learn")
def learn(
    file: Path = typer.Argument(..., exists=True),
    spell: str = typer.Option(..., help="Spell name to learn"),
):
    try:
        pc = load_pc(file)
    except PrettyError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(1) from exc
    learn_spell(pc, spell)
    save_pc(pc, file)
    typer.secho(f"Learned spell: {spell}", fg=typer.colors.GREEN)


@char_app.command("prepare")
def prepare(
    file: Path = typer.Argument(..., exists=True),
    spell: str = typer.Option(..., help="Spell name to prepare"),
):
    pc = load_pc(file)
    try:
        prepare_spell(pc, spell)
    except ValueError as e:
        raise typer.BadParameter(str(e))
    save_pc(pc, file)
    typer.secho(f"Prepared: {spell}", fg=typer.colors.GREEN)


@char_app.command("unprepare")
def unprepare(
    file: Path = typer.Argument(..., exists=True),
    spell: str = typer.Option(...),
):
    pc = load_pc(file)
    unprepare_spell(pc, spell)
    save_pc(pc, file)
    typer.secho(f"Unprepared: {spell}", fg=typer.colors.GREEN)


@char_app.command("cast")
def cast(
    file: Path = typer.Argument(..., exists=True),
    level: int = typer.Option(..., help="Spell slot level to consume (1..9)"),
):
    pc = load_pc(file)
    try:
        cast_slot(pc, level)
    except ValueError as e:
        raise typer.BadParameter(str(e))
    save_pc(pc, file)
    typer.secho(f"Cast: consumed a level {level} slot", fg=typer.colors.GREEN)


@char_app.command("rest")
def rest(
    file: Path = typer.Argument(..., exists=True),
    type: str = typer.Option("long", help="long|short"),
):
    pc = load_pc(file)
    if type == "long":
        long_rest(pc)
    elif type == "short":
        short_rest(pc)
    else:
        raise typer.BadParameter("type must be 'long' or 'short'")
    save_pc(pc, file)
    typer.secho(f"{type.title()} rest complete", fg=typer.colors.GREEN)


@char_app.command("spellstats")
def spellstats(file: Path = typer.Argument(..., exists=True)):
    pc = load_pc(file)
    dc = spell_save_dc(pc)
    atk = spell_attack_bonus(pc)
    if dc is None or atk is None:
        typer.secho("This class has no spellcasting ability defined.", fg=typer.colors.YELLOW)
    else:
        typer.secho(f"Spell Save DC: {dc}  |  Spell Attack: +{atk}", fg=typer.colors.GREEN)


@char_app.command("sheet")
def sheet(
    file: Path = typer.Argument(..., exists=True),
    fmt: str = typer.Option("tty", help="tty|md|pdf"),
    out: Path | None = typer.Option(None, help="Output path for md/pdf"),
    meta: list[str] = typer.Option([], help="Metadata key=value (repeatable)"),
    logo: Path | None = typer.Option(None, help="PDF logo image (png/jpg)"),
    show_zero_slots: bool = typer.Option(
        False, help="Show slot levels with 0 available"
    ),
):
    try:
        pc = load_pc(file)
    except PrettyError as e:
        # Common pitfalls: campaign/party files, stale schema
        if "Additional properties" in str(e):
            typer.secho(
                "This file has fields the schema doesn't know about. "
                "Try upgrading schema (PR 9) or re-saving the PC via 'grimbrain character create'.",
                fg=typer.colors.YELLOW,
            )
        typer.secho(f"Validation failed for {file}:\n{e}", fg=typer.colors.RED)
        raise typer.Exit(1)

    meta_dict: dict[str, str] = {}
    for kv in meta:
        if "=" in kv:
            k, v = kv.split("=", 1)
            meta_dict[k.strip()] = v.strip()

    if fmt == "tty":
        render_console(pc, meta=meta_dict, show_zero_slots=show_zero_slots)
    elif fmt == "md":
        target = (
            out or Path("outputs") / f"{pc.name.replace(' ', '_').lower()}_sheet.md"
        )
        save_markdown(pc, target, meta=meta_dict, show_zero_slots=show_zero_slots)
        typer.secho(f"Wrote {target}", fg=typer.colors.GREEN)
    elif fmt == "pdf":
        target = (
            out or Path("outputs") / f"{pc.name.replace(' ', '_').lower()}_sheet.pdf"
        )
        save_pdf(pc, target, meta=meta_dict, logo=logo, show_zero_slots=show_zero_slots)
        typer.secho(f"Wrote {target}", fg=typer.colors.GREEN)
    else:
        raise typer.BadParameter("Unknown format (use 'tty' or 'md' or 'pdf')")


@char_app.command("equip")
def equip(
    file: Path = typer.Argument(..., exists=True),
    preset: str = typer.Option(
        ..., help="Class or background preset, e.g. 'Wizard' or 'Sage'"
    ),
):
    """Apply a class or background equipment preset to an existing PC."""
    pc = load_pc(file)
    applied = False
    if preset in CLASS_KITS:
        apply_items = CLASS_KITS[preset]
        from grimbrain.characters import apply_items as _apply_items

        _apply_items(pc, apply_items)
        applied = True
    if preset in BACKGROUND_KITS:
        apply_items = BACKGROUND_KITS[preset]
        from grimbrain.characters import apply_items as _apply_items

        _apply_items(pc, apply_items)
        applied = True
    if not applied:
        typer.secho(
            f"Unknown preset '{preset}'. Try a class or background name.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)
    save_pc(pc, file)
    typer.secho(f"Applied '{preset}' kit → {file}", fg=typer.colors.GREEN)
