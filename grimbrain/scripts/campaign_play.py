import random

import typer

from grimbrain.engine.campaign import (
    QuestLogItem,
    advance_time,
    load_campaign,
    save_campaign,
)
from grimbrain.engine.encounters import run_encounter
from grimbrain.engine.shop import PRICES, run_shop

app = typer.Typer(help="Play a lightweight solo campaign loop.")


@app.command()
def travel(
    load: str = typer.Option(..., "--load"),
    hours: int = 4,
    seed: int | None = None,
    force_encounter: bool = typer.Option(False, "--force-encounter", "-F"),
    encounter_chance: int | None = typer.Option(
        None, "--encounter-chance", help="Percent chance (0-100) for overland encounter"
    ),
):
    st = load_campaign(load)
    rng = random.Random(seed if seed is not None else st.seed)
    notes = []
    # PR 44a: allow per-call override and persist it
    if encounter_chance is not None:
        st.encounter_chance = max(0, min(100, encounter_chance))
    advance_time(st, hours=hours)
    res = run_encounter(st, rng, notes, force=force_encounter)
    # Advance stored seed so subsequent travels use a fresh sequence
    st.seed = rng.randrange(1_000_000_000)
    # PR 44b: update the encounter clock based on outcome
    if res.get("encounter") or force_encounter:
        st.encounter_clock = 0
    else:
        step = max(0, getattr(st, "encounter_clock_step", 10))
        st.encounter_clock = min(100, st.encounter_clock + step)
    save_campaign(st, load)
    eff = min(100, st.encounter_chance + st.encounter_clock)
    print(
        f"Day {st.day} {st.time_of_day} @ {st.location} | chance={st.encounter_chance}% + clock={st.encounter_clock}% → effective={eff}%"
    )
    if res.get("encounter"):
        winner = res.get("winner", "?")
        outcome = "Victory!" if winner == "A" else "Defeat..."
        print(f"Encounter: {res['encounter']} — {outcome}")
        if notes:
            print("\n".join(notes))
        hp = ", ".join(
            f"{p.name} {st.current_hp.get(p.id, p.max_hp)}/{p.max_hp}" for p in st.party
        )
        print(f"Party HP: {hp}")
    else:
        # notes already contains "No encounter." in this branch
        print("No encounter.")


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
def shop(
    load: str = typer.Option(..., "--load"),
    script: str | None = typer.Option(None, "--script"),
    seed: int | None = None,
):
    """Buy and sell items using campaign gold and inventory."""
    st = load_campaign(load)
    rng = random.Random(seed if seed is not None else st.seed)
    notes: list[str] = []
    if script:
        data = {"gold": st.gold, "inventory": st.inventory}
        run_shop(data, notes, rng, script)
        st.gold = data["gold"]
        st.inventory = data["inventory"]
        save_campaign(st, load)
        if notes:
            print("\n".join(notes))
        print(f"Leaving shop. Current gold: {st.gold}.")
        return
    items = ", ".join(f"{k} ({v} gp)" for k, v in PRICES.items())
    print(f"Items for sale: {items}")
    while True:
        try:
            raw = input("shop> ").strip()
        except EOFError:
            print()
            break
        if not raw:
            continue
        parts = raw.split()
        op = parts[0].lower()
        if op == "buy" and len(parts) >= 2:
            item = parts[1]
            qty = int(parts[2]) if len(parts) > 2 else 1
            price = PRICES.get(item, 0) * qty
            if st.gold >= price:
                st.gold -= price
                st.inventory[item] = st.inventory.get(item, 0) + qty
                print(f"Bought {qty}× {item} for {price} gp.")
            else:
                print(f"Not enough gold to buy {qty}× {item}.")
        elif op == "sell" and len(parts) >= 2:
            item = parts[1]
            qty = int(parts[2]) if len(parts) > 2 else 1
            have = st.inventory.get(item, 0)
            qty = min(qty, have)
            if qty <= 0:
                print(f"No {item} to sell.")
                continue
            price = int(PRICES.get(item, 0) * 0.5) * qty
            st.inventory[item] = have - qty
            if st.inventory[item] <= 0:
                st.inventory.pop(item, None)
            st.gold += price
            print(f"Sold {qty}× {item} for {price} gp.")
        elif op in {"leave", "exit", "quit"}:
            break
        else:
            print("Unknown command.")
    save_campaign(st, load)
    print(f"Leaving shop. Current gold: {st.gold}.")


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
    elif done:
        for q in st.quest_log:
            if q.id == done:
                q.done = True
                print(f"Completed quest {done}")
    else:
        if st.quest_log:
            for q in st.quest_log:
                status = "Completed" if q.done else "In Progress"
                print(f"{q.id}: {q.text} — {status}")
        else:
            print("No quests.")
    save_campaign(st, load)


if __name__ == "__main__":
    app()
