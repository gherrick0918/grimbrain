from __future__ import annotations

from pathlib import Path

import typer

from grimbrain.validation import load_pc, load_campaign, PrettyError


validate_app = typer.Typer(help="Validate Grimbrain data files")


@validate_app.command()
def pc(file: Path = typer.Argument(..., exists=True)):
    """Validate a PC json file."""
    try:
        _ = load_pc(file)
        typer.secho(f"OK: {file}", fg=typer.colors.GREEN)
    except PrettyError as e:
        typer.secho(f"ERR: {file}\n{e}", fg=typer.colors.RED)
        raise typer.Exit(1)


@validate_app.command()
def campaign(file: Path = typer.Argument(..., exists=True)):
    """Validate a campaign yaml file."""
    try:
        _ = load_campaign(file)
        typer.secho(f"OK: {file}", fg=typer.colors.GREEN)
    except PrettyError as e:
        typer.secho(f"ERR: {file}\n{e}", fg=typer.colors.RED)
        raise typer.Exit(1)


__all__ = ["validate_app"]

