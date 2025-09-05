import random
import typer

from grimbrain.engine.bestiary import make_combatant_from_monster, weapon_names_for_monster
from grimbrain.engine.scene import run_scene

app = typer.Typer(help="Run a fight by monster names (uses bestiary).")


@app.command()
def run(
    a: str = typer.Option(..., "--a", help="Creature name for side A"),
    b: str = typer.Option(..., "--b", help="Creature name for side B"),
    seed: int = 4242,
    rounds: int = 5,
):
    A = make_combatant_from_monster(a, team="A", cid="A")
    B = make_combatant_from_monster(b, team="B", cid="B")
    a_wp, a_off = weapon_names_for_monster(a)
    b_wp, b_off = weapon_names_for_monster(b)
    if a_wp:
        A.weapon = a_wp
    A.offhand = a_off
    if b_wp:
        B.weapon = b_wp
    B.offhand = b_off
    res = run_scene(A, B, seed=seed, max_rounds=rounds)
    print("\n".join(res.log))
    print(
        f"Result: winner = {res.winner} (A_hp={res.a_hp}  B_hp={res.b_hp}) after {res.rounds} round(s) — final distance {res.final_distance_ft}ft"
    )


if __name__ == "__main__":
    app()
