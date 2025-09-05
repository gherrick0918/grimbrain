import random
import typer

from grimbrain.engine.campaign import (
    advance_time,
    load_campaign,
    save_campaign,
    CampaignState,
    QuestLogItem,
)
from grimbrain.engine.encounters import run_encounter

app = typer.Typer(help="Play a lightweight solo campaign loop.")


@app.command()
def travel(load: str = typer.Option(..., "--load"), hours: int = 4, seed: int | None = None):
    st = load_campaign(load)
    rng = random.Random(seed or st.seed)
    notes = []
    advance_time(st, hours=hours)
    res = run_encounter(st, rng, notes)
    save_campaign(st, load)
    print(f"Day {st.day} {st.time_of_day} @ {st.location}")
    print("\n".join(notes))
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
        st.current_hp[p.id] = min(p.max_hp, st.current_hp.get(p.id, p.max_hp) + max(1, heal))
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
