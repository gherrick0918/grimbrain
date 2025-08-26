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
