import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[2]))

import typer

from grimbrain.engine.characters import (
    ABILS,
    STANDARD_ARRAY,
    _parse_scores_from_array,
    _parse_scores_from_kv,
    _point_buy_cost,
    build_partymember,
    save_pc,
)


app = typer.Typer(help="Character creation tools")


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "t", "yes", "y", "1"}:
        return True
    if normalized in {"false", "f", "no", "n", "0"}:
        return False
    raise typer.BadParameter("--ranged expects true/false")


@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def new(
    ctx: typer.Context,
    name: str = typer.Option(..., "--name"),
    klass: str = typer.Option(..., "--class", help="Fighter, Rogue, Wizard (MVP)"),
    weapon: str = typer.Option(..., "--weapon"),
    ranged: str = typer.Option("false", "--ranged", help="true/false"),
    array: str | None = typer.Option(None, "--array", help="e.g. 15,14,13,12,10,8"),
    point_buy: int | None = typer.Option(None, "--point-buy", help="Budget, e.g. 27"),
    scores: str | None = typer.Option(
        None,
        "--scores",
        help="e.g. STR=15 DEX=14 CON=14 INT=10 WIS=10 CHA=8",
    ),
    out: str | None = typer.Option(
        None, "--out", help="Output path; default data/pcs/<name>.json"
    ),
):
    """
    Create a level-1 PC and save to JSON under data/pcs/ by default.
    Provide either --array or (--point-buy and --scores).
    """

    if array:
        scores_map = _parse_scores_from_array(array)
    elif point_buy is not None and scores:
        extras = []
        while ctx.args and "=" in ctx.args[0]:
            extras.append(ctx.args.pop(0))
        tokens = [scores, *extras]
        scores_map = _parse_scores_from_kv(" ".join(tokens))
        if len(scores_map) != len(ABILS):
            missing = [k for k in ABILS if k not in scores_map]
            raise typer.BadParameter(f"Missing {' '.join(missing)} in --scores")
        spent = _point_buy_cost(scores_map)
        if spent > point_buy:
            raise typer.BadParameter(
                f"Point-buy overspent: spent {spent} > budget {point_buy}"
            )
    else:
        scores_map = dict(zip(ABILS, STANDARD_ARRAY))

    ranged_bool = _parse_bool(ranged)

    pc = build_partymember(
        name=name, cls=klass, scores=scores_map, weapon=weapon, ranged=ranged_bool
    )
    out_path = out or f"data/pcs/{name}.json"
    save_pc(pc, out_path)
    typer.echo(f"Saved {name} to {out_path}")


if __name__ == "__main__":
    app()
