import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[2]))

import typer

from grimbrain.engine.campaign import load_campaign, save_campaign
from grimbrain.engine.characters import (
    ABILS,
    STANDARD_ARRAY,
    _parse_scores_from_array,
    _parse_scores_from_kv,
    _point_buy_cost,
    build_partymember,
    pc_summary_line,
    roll_abilities,
    save_pc,
    scores_from_list_desc,
)
from grimbrain.engine.journal import log_event
from grimbrain.engine.srd import find_armor, load_srd


app = typer.Typer(help="Character creation tools")


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "t", "yes", "y", "1"}:
        return True
    if normalized in {"false", "f", "no", "n", "0"}:
        return False
    raise typer.BadParameter("--ranged expects true/false")


@app.command()
def new(
    name: str = typer.Option(..., "--name"),
    klass: str = typer.Option(..., "--class", help="Fighter, Rogue, Wizard (MVP)"),
    weapon: str = typer.Option(..., "--weapon"),
    ranged: str = typer.Option("false", "--ranged", help="true/false"),
    array: str | None = typer.Option(None, "--array", help="e.g. 15,14,13,12,10,8"),
    point_buy: int | None = typer.Option(None, "--point-buy", help="Budget, e.g. 27"),
    scores: str | None = typer.Option(
        None,
        "--scores",
        help="Quoted KV list or CSV: \"STR=15 DEX=14 ...\" or STR=15,DEX=14,...",
    ),
    score: list[str] | None = typer.Option(
        None, "--score", help="Repeatable KV: --score STR=15 --score DEX=14 ..."
    ),
    out: str | None = typer.Option(
        None, "--out", help="Output path; default data/pcs/<name>.json"
    ),
):
    """
    Create a level-1 PC and save to JSON under data/pcs/ by default.
    Provide either --array or (--point-buy and scores via --scores/--score).
    """

    if array:
        scores_map = _parse_scores_from_array(array)
    elif point_buy is not None and (scores or score):
        kv = " ".join(score) if score else scores
        scores_map = _parse_scores_from_kv(kv or "")
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
    out_path = out or _default_pc_path(name)
    save_pc(pc, out_path)
    typer.echo(f"Saved {name} to {out_path}")


def _default_pc_path(name: str) -> str:
    safe_name = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in name)
    safe_name = safe_name.strip("._") or "pc"
    return f"data/pcs/{safe_name}.json"


@app.command(help="Interactive character creator (wizard). Use flags to bypass prompts for CI.")
def create(
    name: str | None = typer.Option(None, "--name"),
    klass: str | None = typer.Option(None, "--class", help="Fighter, Rogue, Wizard (MVP)"),
    method: str | None = typer.Option(None, "--method", help="array | point-buy | roll"),
    array: str | None = typer.Option(None, "--array", help="15,14,13,12,10,8 (for method=array)"),
    point_buy: int = typer.Option(27, "--point-buy", help="Budget for method=point-buy"),
    scores: str | None = typer.Option(
        None,
        "--scores",
        help="STR=15,DEX=14,... (for method=point-buy)",
    ),
    score: list[str] | None = typer.Option(
        None, "--score", help="Repeatable KV for point-buy"
    ),
    weapon: str | None = typer.Option(None, "--weapon"),
    ranged: str | None = typer.Option(None, "--ranged", help="true/false"),
    armor: str | None = typer.Option(None, "--armor", help="Starting armor (blank for none)"),
    shield: str | None = typer.Option(None, "--shield", help="true/false to carry a shield"),
    out: str | None = typer.Option(None, "--out"),
    seed: int | None = typer.Option(
        None, "--seed", help="Deterministic ability rolls for method=roll"
    ),
    log_to: str | None = typer.Option(
        None, "--log-to", help="Optional campaign save to append a journal line"
    ),
):
    """Step-by-step character creator."""

    if not name:
        name = typer.prompt("Name").strip()
    if not name:
        raise typer.BadParameter("Name cannot be blank")

    if not klass:
        klass = typer.prompt("Class (Fighter/Rogue/Wizard)")
    klass = (klass or "").strip().title()
    klass = {"Fighter": "Fighter", "Rogue": "Rogue", "Wizard": "Wizard"}.get(
        klass, klass
    )
    if not klass:
        raise typer.BadParameter("Class cannot be blank")

    try:
        srd = load_srd()
    except FileNotFoundError:
        srd = None

    class_info = None
    if srd is not None:
        for cname, info in srd.classes.items():
            if cname.lower() == klass.lower():
                klass = cname
                class_info = info
                break

    if not method:
        method = typer.prompt("Ability method (array / point-buy / roll)")
    method = (method or "").strip().lower()
    if method not in {"array", "point-buy", "roll"}:
        raise typer.BadParameter("method must be one of: array, point-buy, roll")

    if method == "array":
        if not array:
            default_arr = ",".join(map(str, STANDARD_ARRAY))
            array = typer.prompt("Array scores CSV", default=default_arr)
        scores_map = _parse_scores_from_array(array)
    elif method == "point-buy":
        kv = " ".join(score) if score else scores
        if not kv:
            typer.echo(
                "Enter ability scores like: STR=15,DEX=14,CON=14,INT=10,WIS=10,CHA=8"
            )
            kv = typer.prompt("Scores")
        scores_map = _parse_scores_from_kv(kv or "")
        spent = _point_buy_cost(scores_map)
        if spent > point_buy:
            raise typer.BadParameter(
                f"Point-buy overspent: spent {spent} > budget {point_buy}"
            )
    else:
        rolled = roll_abilities(seed)
        typer.echo(f"Rolled (4d6 drop lowest): {rolled}")
        scores_map = scores_from_list_desc(rolled)

    if not weapon:
        weapon = typer.prompt("Starting weapon (e.g., Longsword, Shortbow)")
    weapon = (weapon or "").strip()
    if not weapon:
        raise typer.BadParameter("Weapon cannot be blank")

    if ranged is None:
        ranged_bool = typer.confirm("Is this a ranged combatant?", default=False)
    else:
        ranged_bool = _parse_bool(ranged)

    default_armor = None
    default_shield = False
    prof_saves = []
    prof_skills = []
    if class_info is not None:
        prof_saves = list(class_info.prof_saves)
        prof_skills = list(class_info.prof_skills)
        for choice in class_info.start_armor:
            if choice.lower() == "shield":
                default_shield = True
            elif default_armor is None and find_armor(choice, srd):
                default_armor = choice

    if armor is not None:
        armor_choice = armor.strip() or None
    else:
        prompt_default = default_armor or ""
        armor_choice = (
            typer.prompt("Armor (empty for none)", default=prompt_default).strip() or None
        )
    if armor_choice and srd is not None:
        armor_obj = find_armor(armor_choice, srd)
        if not armor_obj:
            known = ", ".join(sorted(srd.armors))
            raise typer.BadParameter(f"Unknown armor '{armor_choice}'. Known: {known}")
        armor_choice = armor_obj.name

    if shield is None:
        shield_bool = typer.confirm("Carry a shield?", default=default_shield)
    else:
        shield_bool = _parse_bool(shield)

    summary = pc_summary_line(name, klass, scores_map, weapon, ranged_bool)
    typer.echo(f"\n{summary}")
    if not typer.confirm("Save this character?", default=True):
        raise typer.Exit(1)

    pc = build_partymember(
        name=name,
        cls=klass,
        scores=scores_map,
        weapon=weapon,
        ranged=ranged_bool,
        armor=armor_choice,
        shield=shield_bool,
        prof_skills=prof_skills,
        prof_saves=prof_saves,
    )
    out_path = out or _default_pc_path(name)
    save_pc(pc, out_path)
    typer.echo(f"Saved {name} to {out_path}")

    if log_to:
        state = load_campaign(log_to)
        log_event(state, f"Created {name} the {klass}", kind="create")
        save_campaign(state, log_to)
        typer.echo(f"(Journal updated in {log_to})")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "new":
        sys.argv.pop(1)
    app()
