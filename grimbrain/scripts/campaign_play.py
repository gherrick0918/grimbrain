import random

import typer

from grimbrain.engine.campaign import (
    QuestLogItem,
    advance_time,
    load_campaign,
    save_campaign,
)
from grimbrain.engine.encounters import run_encounter

app = typer.Typer(help="Play a lightweight solo campaign loop.")


@app.command()
def travel(
    load: str = typer.Option(..., "--load"),
    hours: int = 4,
    seed: int | None = None,
    force_encounter: bool = typer.Option(False, "--force-encounter", "-F"),
):
    st = load_campaign(load)
    rng = random.Random(seed if seed is not None else st.seed)
    notes = []
    advance_time(st, hours=hours)
    res = run_encounter(st, rng, notes, force=force_encounter)
    # Advance stored seed so subsequent travels use a fresh sequence
    st.seed = rng.randrange(1_000_000_000)
    save_campaign(st, load)
    print(f"Day {st.day} {st.time_of_day} @ {st.location}")
    if res.get("encounter"):
        winner = res.get("winner", "?")
        outcome = "Victory!" if winner == "A" else "Defeat..."
        print(f"Encounter: {res['encounter']} — {outcome}")
    else:
        print("No encounter.")
    if notes:
        print("\n".join(notes))
    if res:
        print(res)


@app.command()
def explore(load: str = typer.Option(..., "--load"), seed: int | None = None):
    travel(load=load, hours=4, seed=seed)


@app.command()
def short_rest(load: str = typer.Option(..., "--load"), seed: int | None = None):
    st = load_campaign(load)
    rng = random.Random(seed or st.seed)
    notes = []
    for p in st.party:
        heal = rng.randint(1, 8) + p.con_mod
        st.current_hp[p.id] = min(
            p.max_hp, st.current_hp.get(p.id, p.max_hp) + max(1, heal)
        )
        notes.append(f"{p.name} heals {heal} (short rest).")
    save_campaign(st, load)
    print("\n".join(notes))


@app.command()
def long_rest(load: str = typer.Option(..., "--load")):
    st = load_campaign(load)
    for p in st.party:
        st.current_hp[p.id] = p.max_hp
    st.last_long_rest_day = st.day
    save_campaign(st, load)
    print("Long rest: party restored to full and conditions cleared.")


@app.command()
def quest(
    load: str = typer.Option(..., "--load"),
    add: str | None = typer.Option(None, "--add"),
    done: str | None = typer.Option(None, "--done"),
):
    st = load_campaign(load)
    if add:
        qid = f"Q{len(st.quest_log)+1}"
        st.quest_log.append(QuestLogItem(id=qid, text=add, done=False))
        print(f"Added quest {qid}: {add}")
    if done:
        for q in st.quest_log:
            if q.id == done:
                q.done = True
                print(f"Completed quest {done}")
    save_campaign(st, load)


if __name__ == "__main__":
    app()
