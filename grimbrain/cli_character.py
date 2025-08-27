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
)
from grimbrain.sheet import render_console, save_markdown
from grimbrain.sheet_pdf import save_pdf
from grimbrain.validation import PrettyError, load_pc
from grimbrain.rules_equipment import CLASS_KITS, BACKGROUND_KITS

char_app = typer.Typer(help="Character creation and management")


@char_app.command("create")
def create(
    name: str = typer.Option(...),
    klass: str = typer.Option(..., help="Class, e.g. Wizard"),
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
        klass=klass,
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
    klass: str = typer.Option(...),
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
        klass=klass,
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
    klass: str = typer.Option(...),
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
        klass=klass,
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
        raise typer.BadParameter(
            f"Unknown preset '{preset}'. Try a class or background name."
        )
    save_pc(pc, file)
    typer.secho(f"Applied '{preset}' kit → {file}", fg=typer.colors.GREEN)
