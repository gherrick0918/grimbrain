import random
from pathlib import Path

import typer

from grimbrain.engine.campaign import (
    QuestLogItem,
    advance_time,
    load_campaign,
    save_campaign,
    load_yaml_campaign,
    load_party,
    CampaignState,
    PartyMemberRef,
    party_to_combatants,
    apply_combat_results,
)
from grimbrain.engine.bestiary import make_combatant_from_monster, weapon_names_for_monster
from grimbrain.engine.encounters import run_encounter
from grimbrain.engine.loot import roll_loot
from grimbrain.engine.progression import award_xp, maybe_level_up
from grimbrain.engine.shop import PRICES, run_shop
from grimbrain.engine.skirmish import run_skirmish


def _default_party() -> list[PartyMemberRef]:
    return [
        PartyMemberRef(
            id="PC1",
            name="Fighter",
            str_mod=3,
            dex_mod=1,
            con_mod=2,
            int_mod=0,
            wis_mod=0,
            cha_mod=0,
            ac=16,
            max_hp=24,
            pb=2,
            speed=30,
            weapon_primary="Longsword",
        ),
        PartyMemberRef(
            id="PC2",
            name="Archer",
            str_mod=0,
            dex_mod=3,
            con_mod=1,
            int_mod=0,
            wis_mod=0,
            cha_mod=0,
            ac=14,
            max_hp=16,
            pb=2,
            speed=30,
            ranged=True,
            weapon_primary="Longbow",
        ),
    ]


def _pc_to_ref(pc, idx: int) -> PartyMemberRef:
    atk = pc.attacks[0] if getattr(pc, "attacks", []) else None
    weapon = atk.name if atk else None
    ranged = atk.type == "ranged" if atk else False
    return PartyMemberRef(
        id=f"PC{idx}",
        name=pc.name,
        str_mod=getattr(pc, "str_mod", 0),
        dex_mod=getattr(pc, "dex_mod", 0),
        con_mod=getattr(pc, "con_mod", 0),
        int_mod=getattr(pc, "int_mod", 0),
        wis_mod=getattr(pc, "wis_mod", 0),
        cha_mod=getattr(pc, "cha_mod", 0),
        ac=pc.ac,
        max_hp=pc.max_hp,
        pb=getattr(pc, "pb", getattr(pc, "prof_bonus", 2)),
        speed=getattr(pc, "speed", 30),
        ranged=ranged,
        weapon_primary=weapon,
    )


def _parse_enemies(enc: str | list[str] | None) -> list[str]:
    import re

    if enc is None:
        return []
    if isinstance(enc, list):
        names: list[str] = []
        for e in enc:
            names.extend(_parse_enemies(e))
        return names
    text = str(enc).strip()
    m = re.match(r"(.+) x(\d+)", text)
    if m:
        name = m.group(1).strip()
        count = int(m.group(2))
        return [name] * count
    return [text]

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
def story(file: str = typer.Argument(..., help="Path to campaign YAML")):
    camp = load_yaml_campaign(file)
    base = Path(file).resolve().parent
    pcs = load_party(camp, base)
    if pcs:
        party = [_pc_to_ref(pc, i + 1) for i, pc in enumerate(pcs)]
    else:
        party = _default_party()
    state = CampaignState(seed=camp.seed or 0, party=party)
    for p in state.party:
        state.current_hp[p.id] = p.max_hp
    rng = random.Random(camp.seed or 0)
    current = camp.start
    while True:
        scene = camp.scenes[current]
        print(scene.text)

        if scene.check:
            chk = scene.check
            pc = state.party[0]
            mod = 0
            if chk.skill:
                skill = chk.skill.lower()
                if skill == "athletics":
                    mod = pc.str_mod + (pc.pb if pc.prof_athletics else 0)
                elif skill == "acrobatics":
                    mod = pc.dex_mod + (pc.pb if pc.prof_acrobatics else 0)
            elif chk.ability:
                ab = chk.ability.lower()
                mod = getattr(pc, f"{ab}_mod", 0)
            roll1 = rng.randint(1, 20)
            roll2 = rng.randint(1, 20) if chk.advantage else None
            roll = max(roll1, roll2) if chk.advantage else roll1
            total = roll + mod
            result = "success" if total >= chk.dc else "failure"
            if chk.advantage:
                print(
                    f"(Skill check: rolled {roll1} and {roll2} + {mod} = {total} vs DC {chk.dc} — {result})"
                )
            else:
                print(
                    f"(Skill check: rolled {roll1} + {mod} = {total} vs DC {chk.dc} — {result})"
                )
            if total >= chk.dc and chk.on_success:
                current = chk.on_success
                continue
            if total < chk.dc and chk.on_failure:
                current = chk.on_failure
                continue

        if scene.encounter:
            enemies = _parse_enemies(scene.encounter)
            allies_map = party_to_combatants(state)
            foes = []
            for idx, name in enumerate(enemies, 1):
                cmb = make_combatant_from_monster(name, team="B", cid=f"E{idx}")
                wp, off = weapon_names_for_monster(name)
                if wp:
                    cmb.weapon = wp
                cmb.offhand = off
                foes.append(cmb)
            roster = list(allies_map.values()) + foes
            res = run_skirmish(roster, seed=rng.randint(1, 999999))
            apply_combat_results(state, allies_map)
            winner = res.get("winner")
            outcome = "Victory" if winner == "A" else "Defeat"
            print(
                f"(Combat resolved: {outcome} over {', '.join(enemies)} in {res['rounds']} rounds)"
            )
            if winner == "A":
                notes: list[str] = []
                pcs_data = []
                for p in state.party:
                    pdata = {
                        "id": p.id,
                        "name": p.name,
                        "xp": p.xp,
                        "level": p.level,
                        "max_hp": p.max_hp,
                        "con_mod": p.con_mod,
                        "pb": p.pb,
                        "hp": state.current_hp.get(p.id, p.max_hp),
                    }
                    pcs_data.append((p, pdata))
                award_xp(enemies, [d for _, d in pcs_data], notes)
                for p, pdata in pcs_data:
                    p.xp = pdata["xp"]
                for p, pdata in pcs_data:
                    if maybe_level_up(pdata, rng, notes):
                        p.level = pdata["level"]
                        p.max_hp = pdata["max_hp"]
                        p.pb = pdata["pb"]
                        state.current_hp[p.id] = pdata["hp"]
                loot = roll_loot(enemies, rng, notes)
                state.gold += loot.get("gold", 0)
                for item, qty in loot.items():
                    if item == "gold":
                        continue
                    state.inventory[item] = state.inventory.get(item, 0) + qty
                if notes:
                    print("\n".join(notes))
                if scene.on_victory:
                    current = scene.on_victory
                    continue
            else:
                if scene.on_defeat:
                    current = scene.on_defeat
                    continue
                print("All heroes have fallen. Game over.")
                return

        if scene.rest:
            if scene.rest == "long":
                for p in state.party:
                    state.current_hp[p.id] = p.max_hp
                print("The party takes a long rest and recovers fully.")
            elif scene.rest == "short":
                for p in state.party:
                    heal = rng.randint(1, 8) + p.con_mod
                    state.current_hp[p.id] = min(
                        p.max_hp,
                        state.current_hp.get(p.id, p.max_hp) + max(1, heal),
                    )
                print("The party takes a short rest and recovers some health.")

        if scene.choices:
            for idx, choice in enumerate(scene.choices, 1):
                print(f"{idx}. {choice.text}")
            sel: int | None = None
            while sel is None:
                try:
                    raw = input("choice> ").strip()
                except EOFError:
                    return
                if raw.isdigit():
                    num = int(raw)
                    if 1 <= num <= len(scene.choices):
                        sel = num
                        break
                print("Invalid choice.")
            current = scene.choices[sel - 1].next
            continue
        else:
            print("(End of story)")
            break


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
