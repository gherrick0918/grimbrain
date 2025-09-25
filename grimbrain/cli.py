from __future__ import annotations

from functools import partial
from pathlib import Path
import sys
from typing import List

import typer
from rich import box

try:
    import typer.rich_utils as tru
except ModuleNotFoundError:  # pragma: no cover - older Typer versions
    tru = None

from grimbrain.cli_character import char_app, equip
from grimbrain.cli_validate import validate_app

if tru is not None:  # pragma: no branch
    tru.Panel = partial(tru.Panel, box=box.ASCII)


HELP_TEXT = """Usage: grimbrain [OPTIONS] COMMAND [ARGS]...

Grimbrain - solo D&D 5e engine (local-first).

Commands:
  play       Run a single encounter using the engine.
  content    Helpers for managing local content caches.
  validate   Validate player character or campaign data.
  character  Character creation and management tools.
"""

app = typer.Typer(no_args_is_help=True)
app.add_typer(validate_app, name="validate")
app.add_typer(char_app, name="character")


def _print_help() -> None:
    typer.echo(HELP_TEXT.strip())


def _handle_character(args: List[str]) -> int:
    if not args or args[0] in {"-h", "--help"}:
        typer.echo("Usage: grimbrain character equip <FILE> --preset <NAME>")
        return 0

    subcommand = args.pop(0)
    if subcommand != "equip":
        typer.echo(f"Unknown character subcommand: {subcommand}", err=True)
        return 1

    if not args:
        typer.echo("Usage: grimbrain character equip <FILE> --preset <NAME>", err=True)
        return 1

    file_arg = args.pop(0)
    preset: str | None = None
    it = iter(args)
    for token in it:
        if token == "--preset":
            try:
                preset = next(it)
            except StopIteration:
                typer.echo("--preset requires a value", err=True)
                return 1
        else:
            typer.echo(f"Unrecognized option '{token}'", err=True)
            return 1

    if preset is None:
        typer.echo("Missing required option --preset", err=True)
        return 1

    try:
        result = equip(Path(file_arg), preset=preset)
    except typer.Exit as exc:
        code = getattr(exc, "code", None)
        if code is None and exc.args:
            code = exc.args[0]
        return int(code or 0)
    return 0 if result is None else result


def run_cli(argv: List[str] | None = None) -> int:
    args = list(argv or sys.argv[1:])
    if not args or args[0] in {"-h", "--help"}:
        _print_help()
        return 0

    command = args.pop(0)
    if command == "character":
        return _handle_character(args)
    if command == "content":
        if args and args[0] == "reload":
            typer.echo("Rebuilt content/rules indexes (stub)")
            return 0
        typer.echo("Unknown content subcommand", err=True)
        return 1
    if command == "play":
        typer.echo("play command not implemented", err=True)
        return 1

    typer.echo(f"Unknown command: {command}", err=True)
    return 1


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
    # raise typer.Exit(result.returncode)
    typer.echo("play command not implemented", err=True)
    raise typer.Exit(1)


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
    raise SystemExit(run_cli())
