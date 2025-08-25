from __future__ import annotations

import os
from functools import partial
from pathlib import Path

from rich import box
import typer
import typer.rich_utils as tru

tru.Panel = partial(tru.Panel, box=box.ASCII)

app = typer.Typer(no_args_is_help=True)


@app.callback()
def main() -> None:
    """Grimbrain - solo D&D 5e engine (local-first)."""


@app.command()
def play(
    pc: Path = typer.Option(..., exists=True, help="PC file (json)"),
    encounter: str = typer.Option(..., help="Encounter id (e.g., 'goblin')"),
    packs: str = typer.Option("srd", help="Comma-separated pack ids"),
    seed: int = typer.Option(1, help="Deterministic RNG seed"),
    md_out: Path | None = typer.Option(None, help="Markdown log output"),
    json_out: Path | None = typer.Option(None, help="NDJSON sidecar output"),
    autosave: bool = typer.Option(False, help="Append turn summaries"),
    debug: bool = typer.Option(False, help="Verbose resolver logs"),
) -> None:
    """Run a single encounter using the engine."""
    # TODO: import and call your existing engine runner here.
    # Example:
    # from grimbrain.engine import run_encounter
    # result = run_encounter(pc, encounter, packs.split(','), seed, md_out, json_out, autosave, debug)
    # typer.Exit(code=result.returncode)
    typer.echo(f"[grimbrain] seed={seed} packs={packs} encounter={encounter}")


@app.command()
def content(
    reload: bool = typer.Option(
        False, "--reload", help="Rebuild content/rules indexes"
    ),
) -> None:
    if reload:
        # from grimbrain.content import rebuild_indexes
        # rebuild_indexes()
        typer.echo("Rebuilt content/rules indexes (stub)")


if __name__ == "__main__":
    app()
