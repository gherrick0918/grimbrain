import random
import sys
from pathlib import Path
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[2]))

import typer
from typer.models import ArgumentInfo, OptionInfo

from grimbrain.engine.campaign import (
    QuestLogItem,
    advance_time,
    load_campaign,
    save_campaign,
    load_yaml_campaign,
    load_party,
    PartyMemberRef,
    party_to_combatants,
    apply_combat_results,
    CampaignState,
)
from grimbrain.engine.bestiary import make_combatant_from_monster, weapon_names_for_monster
from grimbrain.engine.encounters import run_encounter
from grimbrain.engine.loot import roll_loot
from grimbrain.engine.progression import award_xp, maybe_level_up
from grimbrain.engine.shop import PRICES, run_shop
from grimbrain.engine.skirmish import run_skirmish
from grimbrain.engine.narrator import get_narrator
from grimbrain.engine.config import load_config, save_config, choose_ai_enabled
from grimbrain.engine.journal import format_entries, log_event, write_export


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


def _party_status_line(st: CampaignState) -> str:
    parts: list[str] = []
    hp = getattr(st, "current_hp", {}) or {}
    for pm in st.party:
        cur = hp.get(pm.id, pm.max_hp)
        parts.append(f"{pm.name} {cur}/{pm.max_hp}")
    gold = getattr(st, "gold", 0)
    return f"Party: {', '.join(parts)} | Gold: {gold}"

app = typer.Typer(help="Play a lightweight solo campaign loop.")


@app.command(help="Set or show local Grimbrain config (~/.grimbrain/config.json)")
def config(
    set_openai_key: str = typer.Option(
        None, "--set-openai-key", help="Store an OpenAI API key locally"
    ),
    enable_ai: bool = typer.Option(
        None, "--enable-ai/--disable-ai", help="Toggle AI narration"
    ),
    show: bool = typer.Option(False, "--show", help="Print current config (keys redacted)"),
):
    cfg = load_config()
    changed = False
    if set_openai_key is not None:
        cfg["openai_api_key"] = set_openai_key
        cfg.pop("OPENAI_API_KEY", None)
        changed = True
    if enable_ai is not None:
        cfg["GRIMBRAIN_AI"] = "1" if enable_ai else "0"
        changed = True
    if changed:
        save_config(cfg)
        print("Config saved.")
    if show:
        redacted: dict[str, Any] = {}
        for key, value in cfg.items():
            if isinstance(value, str) and key.lower().endswith("api_key") and value:
                suffix = value[-4:] if len(value) >= 4 else value
                redacted[key] = "****" + suffix
            else:
                redacted[key] = value
        print(redacted)


def _cli_value(value: Any) -> Any:
    """Normalize Typer default placeholders to regular Python values."""

    if isinstance(value, (OptionInfo, ArgumentInfo)):
        return None
    return value


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
    eff = min(100, st.encounter_chance + st.encounter_clock)
    if res.get("encounter"):
        winner = res.get("winner", "?")
        rounds = res.get("rounds")
        outcome = "Victory" if winner == "A" else "Defeat"
        summary = f"Travel {hours}h; Encounter {res['encounter']} — {outcome}"
        if isinstance(rounds, int):
            summary += f" in {rounds} rounds"
        log_event(
            st,
            summary,
            kind="travel",
            extra={
                "chance": st.encounter_chance,
                "clock": st.encounter_clock,
                "effective": eff,
            },
        )
    else:
        log_event(
            st,
            f"Travel {hours}h; No encounter",
            kind="travel",
            extra={
                "chance": st.encounter_chance,
                "clock": st.encounter_clock,
                "effective": eff,
            },
        )
    save_campaign(st, load)
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
def status(load: str = typer.Option(..., "--load")):
    """
    Print day/time, location, encounter chance/clock, party HP, and a couple inventory counts.
    """

    st = load_campaign(load)
    chance = getattr(st, "encounter_chance", 30)
    clock = getattr(st, "encounter_clock", 0)
    eff = min(100, chance + clock)
    print(
        f"Day {st.day} {st.time_of_day} @ {st.location} | "
        f"chance={chance}% + clock={clock}% → effective={eff}%"
    )
    print(_party_status_line(st))
    inv = getattr(st, "inventory", {}) or {}
    key_items = [k for k in ("potion_healing", "ammo_arrows") if k in inv]
    if key_items:
        print("Inventory:", ", ".join(f"{k}={inv[k]}" for k in key_items))


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
    log_event(st, "Short rest", kind="rest", extra={"type": "short"})
    # PR49: advance time by configured short rest hours
    advance_time(st, hours=getattr(st, "short_rest_hours", 4))
    save_campaign(st, load)
    print("\n".join(notes))


@app.command()
def long_rest(load: str = typer.Option(..., "--load")):
    st = load_campaign(load)
    for p in st.party:
        st.current_hp[p.id] = p.max_hp
    st.last_long_rest_day = st.day
    log_event(st, "Long rest", kind="rest", extra={"type": "long"})
    # PR49: advance to next morning if configured
    if getattr(st, "long_rest_to_morning", True):
        # advance at least one segment then roll until morning
        advance_time(st, hours=4)
        while st.time_of_day != "morning":
            advance_time(st, hours=4)
    save_campaign(st, load)
    print("Long rest: party restored to full and conditions cleared.")


@app.command()
def story(
    file: str | None = typer.Argument(None, help="Path to story YAML"),
    load: str | None = typer.Option(
        None, "--load", help="Optional campaign state JSON to persist progress"
    ),
    story: str | None = typer.Option(
        None, "--story", help="Path to story YAML (overrides positional argument)"
    ),
    ai: str | None = typer.Option(
        None, "--ai", help="'on'/'off' to override env/config narration setting"
    ),
    flush_cache: bool = typer.Option(
        False, "--flush-cache", help="Bypass narration cache for this run"
    ),
    narration_debug: bool = typer.Option(
        False,
        "--narration-debug",
        help="Print AI/cache information when rendering narration",
    ),
):
    """Play a scripted story scene-by-scene, tracking simple campaign flags."""

    load_path = _cli_value(load)
    story_path = _cli_value(story)
    file_path = _cli_value(file)
    ai = _cli_value(ai)
    if not story_path:
        story_path = file_path
    if not story_path and isinstance(load_path, str) and load_path.lower().endswith((".yaml", ".yml")):
        story_path = load_path
        load_path = None
    if not story_path:
        raise typer.BadParameter("Provide a story YAML via --story or positional argument.")

    raw_story = Path(str(story_path)).expanduser()
    search: list[Path] = [raw_story]
    if not raw_story.is_absolute():
        search.append(Path.cwd() / raw_story)
        search.append(Path("data/stories") / raw_story)

    story_file: Path | None = None
    tried: list[Path] = []
    for candidate in search:
        if candidate.exists():
            story_file = candidate
            break
        tried.append(candidate)

    if story_file is None:
        tried_text = ", ".join(str(p.resolve()) for p in tried)
        raise typer.BadParameter(f"Story file not found. Tried: {tried_text}")

    camp = load_yaml_campaign(str(story_file))
    base = story_file.resolve().parent
    pcs = load_party(camp, base)

    if load_path:
        state = load_campaign(load_path)
    else:
        state = CampaignState(seed=camp.seed or 0)
    if not state.party:
        if pcs:
            state.party = [_pc_to_ref(pc, i + 1) for i, pc in enumerate(pcs)]
        else:
            state.party = _default_party()
    for p in state.party:
        state.current_hp.setdefault(p.id, p.max_hp)

    rng_seed = camp.seed if camp.seed is not None else state.seed
    rng = random.Random(rng_seed or 0)
    ai_enabled = choose_ai_enabled(ai)
    narrator = get_narrator(
        ai_enabled=ai_enabled, debug=bool(narration_debug), flush=bool(flush_cache)
    )
    if narration_debug:
        src = "flag" if ai is not None else "env/config"
        print(f"[narration] effective_ai={'ON' if ai_enabled else 'OFF'} (source={src})")

    flags_obj = state.inventory.setdefault("_flags", [])
    if isinstance(flags_obj, list):
        flags: list[str] = flags_obj
    elif isinstance(flags_obj, (set, tuple)):
        flags = list(flags_obj)
        state.inventory["_flags"] = flags
    elif flags_obj:
        flags = [str(flags_obj)]
        state.inventory["_flags"] = flags
    else:
        flags = []
        state.inventory["_flags"] = flags

    def persist() -> None:
        if load_path:
            save_campaign(state, load_path)

    def apply_flags(scene_obj) -> None:
        for flag in getattr(scene_obj, "set_flags", []) or []:
            if flag and flag not in flags:
                flags.append(flag)

    current = camp.start
    while True:
        scene = camp.scenes[current]
        ctx = {
            "day": state.day,
            "time_of_day": state.time_of_day,
            "party_gold": getattr(state, "gold", 0),
            "pc1_name": state.party[0].name if state.party else "Hero",
            "location": state.location,
            "scene_id": scene.id,
            "flags": ", ".join(flags),
            "party_names": ", ".join(p.name for p in state.party) if state.party else "Hero",
        }

        log_event(
            state,
            f"Story scene: {scene.id}",
            kind="story",
            extra={"scene": scene.id},
        )

        missing = [req for req in scene.requires if req and req not in flags]
        if missing:
            print(f"(You lack: {', '.join(missing)})")
            persist()
            break

        if scene.text:
            print(narrator.render(scene.id, scene.text, ctx))

        if scene.if_flag and scene.if_flag.flag and scene.if_flag.flag in flags:
            cond_text = scene.if_flag.text or ""
            if cond_text:
                print(narrator.render(f"{scene.id}#if", cond_text, ctx))

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
                apply_flags(scene)
                persist()
                current = chk.on_success
                continue
            if total < chk.dc and chk.on_failure:
                apply_flags(scene)
                persist()
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
            rounds = res.get("rounds")
            detail = f"Story encounter {', '.join(enemies)} — {outcome}"
            if isinstance(rounds, int):
                detail += f" in {rounds} rounds"
            log_event(
                state,
                detail,
                kind="story_encounter",
                extra={"scene": scene.id, "rounds": rounds},
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
                    apply_flags(scene)
                    persist()
                    current = scene.on_victory
                    continue
            else:
                if scene.on_defeat:
                    apply_flags(scene)
                    persist()
                    current = scene.on_defeat
                    continue
                print("All heroes have fallen. Game over.")
                apply_flags(scene)
                persist()
                return

        if scene.rest:
            if scene.rest == "long":
                for p in state.party:
                    state.current_hp[p.id] = p.max_hp
                print("The party takes a long rest and recovers fully.")
                if getattr(state, "long_rest_to_morning", True):
                    advance_time(state, hours=4)
                    while state.time_of_day != "morning":
                        advance_time(state, hours=4)
                log_event(
                    state,
                    "Story rest: long",
                    kind="story_rest",
                    extra={"scene": scene.id, "type": "long"},
                )
            elif scene.rest == "short":
                for p in state.party:
                    heal = rng.randint(1, 8) + p.con_mod
                    state.current_hp[p.id] = min(
                        p.max_hp,
                        state.current_hp.get(p.id, p.max_hp) + max(1, heal),
                    )
                print("The party takes a short rest and recovers some health.")
                advance_time(state, hours=getattr(state, "short_rest_hours", 4))
                log_event(
                    state,
                    "Story rest: short",
                    kind="story_rest",
                    extra={"scene": scene.id, "type": "short"},
                )

        if scene.choices:
            for idx, choice in enumerate(scene.choices, 1):
                print(f"{idx}. {choice.text}")
            sel: int | None = None
            while sel is None:
                try:
                    raw = input("choice> ").strip()
                except EOFError:
                    apply_flags(scene)
                    persist()
                    return
                if raw.isdigit():
                    num = int(raw)
                    if 1 <= num <= len(scene.choices):
                        sel = num
                        break
                print("Invalid choice.")
            choice_obj = scene.choices[sel - 1]
            log_event(
                state,
                f"Story choice: {scene.id} → {choice_obj.next}",
                kind="story",
                extra={"scene": scene.id, "choice": choice_obj.text},
            )
            apply_flags(scene)
            persist()
            current = choice_obj.next
            continue
        else:
            apply_flags(scene)
            persist()
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
                log_event(
                    st,
                    f"Shop: bought {item} x{qty} for {price} gp",
                    kind="shop",
                    extra={"item": item, "qty": qty, "gp": price, "op": "buy"},
                )
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
            log_event(
                st,
                f"Shop: sold {item} x{qty} for {price} gp",
                kind="shop",
                extra={"item": item, "qty": qty, "gp": price, "op": "sell"},
            )
        elif op in {"leave", "exit", "quit"}:
            break
        else:
            print("Unknown command.")
    save_campaign(st, load)
    print(f"Leaving shop. Current gold: {st.gold}.")


@app.command()
def journal(
    load: str = typer.Option(..., "--load"),
    tail: int | None = typer.Option(None, "--tail", help="Show only the last N entries"),
    grep: str | None = typer.Option(None, "--grep", help="Filter entries containing text"),
    clear: bool = typer.Option(False, "--clear", help="Erase the journal after showing"),
    style: str = typer.Option("compact", "--style", help="compact|detailed"),
    export: str | None = typer.Option(None, "--export", help="Write to path (.md or .txt)"),
):
    """Print or export the adventure log from the campaign save."""

    st = load_campaign(load)
    entries = list(getattr(st, "journal", []) or [])
    if grep:
        needle = grep.lower()
        entries = [e for e in entries if needle in (e.get("text", "").lower())]
    if tail is not None and tail > 0:
        entries = entries[-tail:]

    export_path = export if isinstance(export, str) else None
    if export_path:
        write_export(entries, export_path, style=style)
        print(f"Exported journal to {export_path}")
    else:
        lines = format_entries(entries, style=style)
        if lines:
            print("\n".join(lines))
        else:
            print("(Journal is empty.)")
    if clear:
        st.journal = []
        save_campaign(st, load)
        print("(Journal cleared.)")


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
        log_event(
            st,
            f"Quest added: {qid} — {add}",
            kind="quest",
            extra={"id": qid, "op": "add"},
        )
    elif done:
        found = False
        for q in st.quest_log:
            if q.id == done:
                q.done = True
                print(f"Completed quest {done}")
                found = True
        if found:
            log_event(
                st,
                f"Quest completed: {done}",
                kind="quest",
                extra={"id": done, "op": "done"},
            )
    else:
        if st.quest_log:
            for q in st.quest_log:
                status = "Completed" if q.done else "In Progress"
                print(f"{q.id}: {q.text} — {status}")
        else:
            print("No quests.")
    save_campaign(st, load)


def campaign_loop(path: str) -> None:
    """Interactive loop allowing continuous campaign play."""
    state = load_campaign(path)
    print("Entering campaign loop. Type 'help' for options.")
    while True:
        hp = ", ".join(
            f"{p.name} {state.current_hp.get(p.id, p.max_hp)}/{p.max_hp}"
            for p in state.party
        )
        print(
            f"Day {state.day} {state.time_of_day} @ {state.location} | Party: {hp} | Gold: {state.gold}"
        )
        try:
            raw = input(
                "Choose action: [T]ravel, [R]est, [Q]uest log, [S]hop, [X] Exit > "
            ).strip().lower()
        except EOFError:
            print()
            break
        if not raw:
            continue
        if raw in {"t", "travel"}:
            travel(load=path)
            state = load_campaign(path)
        elif raw in {"r", "rest"}:
            try:
                kind = input("Short or long rest? (s/l) > ").strip().lower()
            except EOFError:
                break
            if kind.startswith("s"):
                short_rest(load=path)
                state = load_campaign(path)
            elif kind.startswith("l"):
                long_rest(load=path)
                state = load_campaign(path)
            else:
                print("Rest cancelled.")
        elif raw in {"q", "quest", "quests"}:
            if state.quest_log:
                for q in state.quest_log:
                    status = "Completed" if q.done else "In Progress"
                    print(f"{q.id}: {q.text} — {status}")
            else:
                print("No quests.")
        elif raw in {"s", "shop"}:
            save_campaign(state, path)
            shop(load=path, script=None)
            state = load_campaign(path)
        elif raw in {"x", "exit", "quit"}:
            save_campaign(state, path)
            print("Exiting campaign.")
            break
        elif raw in {"h", "help", "menu"}:
            print("Commands: [T]ravel, [R]est, [Q]uest log, [S]hop, [X] Exit")
        else:
            print("Unknown command.")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context, load: str = typer.Option(None, "--load")):
    if ctx.invoked_subcommand is None:
        if not load:
            typer.echo("--load is required to start the campaign loop")
            raise typer.Exit(1)
        campaign_loop(load)
        raise typer.Exit()


if __name__ == "__main__":
    app()
