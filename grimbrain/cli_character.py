from __future__ import annotations

from pathlib import Path

import typer

from grimbrain.characters import PCOptions, create_pc, level_up, save_pc
from grimbrain.validation import PrettyError, load_pc

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
    arr: str = typer.Option("15,14,13,12,10,8", help="Comma-sep standard array (high->low)"),
    assign: str = typer.Option(
        "int,dex,con,str,wis,cha", help="Order to assign stats (comma sep)"
    ),
    out: Path = typer.Option(Path("pc.json")),
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
