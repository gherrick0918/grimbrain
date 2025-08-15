from typing import Any, Dict, List, Optional
import re

REST_RE = re.compile(r'^rest\s+(short|long)\s+([A-Za-z][\w\s\'"-]+)(?:\s+(\d+))?$', re.I)
CAST_RE = re.compile(r'^cast\s+"([^"]+)"(?:\s+"([^"]+)")?(?:\s+--level\s+(\d+))?$', re.I)
REACTION_RE = re.compile(r'^reaction\s+"([^"]+)"\s+([A-Za-z][\w\s\'"-]+)$', re.I)

# -- snip other imports --

def finalize_result(
    winner: str,
    combatants: "List[Combatant]",
    monsters: Optional[List[Any]] = None,
    rounds: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Build a stable encounter result payload for the campaign runner.
    - winner: "party" or "monsters"
    - combatants: full list; we'll extract party HP
    - monsters: optional, in case you later compute XP/loot here
    - rounds: optional, include if you track it
    """
    outcome = "victory" if str(winner).lower() == "party" else "defeat"
    party_hp = {
        getattr(c, "name", f"pc-{i}"): (0 if getattr(c, "defeated", False) else int(getattr(c, "hp", 0)))
        for i, c in enumerate(combatants)
        if getattr(c, "side", "") == "party"
    }
    summary = {
        "winner": winner,
        "rounds": rounds,
    }
    return {"result": outcome, "summary": summary, "hp": party_hp}

import argparse
import csv
import json
import os
import random
import shlex
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from collections import defaultdict
from dataclasses import replace

from grimbrain.engine.session import Session, start_scene, log_step
from grimbrain.engine.combat import (
    run_round,
    run_encounter,
    parse_monster_spec,
    choose_target,
    Combatant,
)
from grimbrain.engine.dice import roll
from grimbrain.engine import checks, rests
from grimbrain.models import PC, MonsterSidecar, dump_model
from grimbrain.campaign import load_party_file
from grimbrain.engine import campaign as campaign_engine
from grimbrain.engine.logger import SessionLogger
from grimbrain.fallback_monsters import FALLBACK_MONSTERS
from grimbrain.engine.encounter import compute_encounter, apply_difficulty
from grimbrain.content.packs import load_packs
from grimbrain.content.select import select_monster
from grimbrain import pc_wizard
from grimbrain.rules import (
    ActionState,
    apply_dodge,
    clear_dodge,
    apply_help,
    apply_hide,
    derive_attack_advantage,
    consume_one_shot_flags,
    combine_adv,
    ConditionFlags,
    derive_condition_advantage,
    roll_save,
)
from grimbrain.cli_helpers import (
    _apply_damage,
    heal_target,
    _print_status,
    _check_victory,
    _save_game,
    _load_game,
    _normalize_cmd,
)

LOG_FILE = f"logs/index_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
log_entries = []


def choose_embedding(mode: str):
    if mode == "none":
        os.environ["SUPPRESS_EMBED_WARNING"] = "1"
        return None, "Embeddings disabled"
    try:
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding
        embed = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
        return embed, f"Using embedding model: {embed.model_name}"
    except Exception as e:
        if mode == "bge-small":
            return None, f"Failed to load BGE small: {e}"
        return None, f"Embedding model unavailable: {e}"


def write_outputs(md: str, js: dict | None, json_out: str | None, md_out: str | None) -> None:
    if json_out and js:
        path = Path(json_out)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(js, f, indent=2)
        print(f"Sidecar JSON written to {path}")
    if md_out:
        path = Path(md_out)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"Markdown written to {path}")


def _normalize_party(raw: list[dict]) -> list[dict]:
    """Normalize attack keys in PC JSON."""
    def _normalize_pc(obj: dict) -> dict:
        attacks = obj.get("attacks", [])
        for atk in attacks:
            if "damage_dice" not in atk and "damage" in atk:
                atk["damage_dice"] = atk.pop("damage")
            if "to_hit" not in atk and "attack_bonus" in atk:
                atk["to_hit"] = atk["attack_bonus"]
        return obj

    return [_normalize_pc(o) for o in raw]


def _lookup_fallback(name):
    if name.lower() == "none":
        return None
    data = FALLBACK_MONSTERS[name.lower()]
    return MonsterSidecar(**data)  # <-- wrap in MonsterSidecar



def play_cli(
    pcs: list[PC],
    monsters: list[MonsterSidecar],
    seed: int | None = None,
    max_rounds: int = 20,
    autosave: bool = False,
    summary_out: str | None = None,
    script=None,  # <-- add this parameter
) -> dict | None:
    import sys
    import shlex

    def make_input(script_file):
        # --script wins
        if script_file is not None:
            def _read(_prompt):
                raw = script_file.readline()
                if raw == "":        # EOF -> end cleanly (many tests expect this)
                    return "q"
                s = raw.strip()
                print(f"> {s}")      # echo for logs/tests
                return s
            return _read
        # If stdin is piped by tests, use readline so prompts don’t block
        if not sys.stdin.isatty():
            def _read(_prompt):
                raw = sys.stdin.readline()
                if raw == "":
                    return "q"
                return raw.strip()
            return _read
        # Interactive fallback
        return lambda prompt: input(prompt).strip()

    input_fn = make_input(script)

    # RNG for deterministic runs in tests & CLI
    rng = random.Random(seed) if seed is not None else random.Random()

    # --- PATCH END ---

    script_stream = script  # this will be a file handle or None
    input_lines: list[str] | None = None
    input_iter = iter([])
    if not sys.stdin.isatty():
        input_lines = [line.rstrip("\n") for line in sys.stdin]
        input_iter = iter(input_lines)

    combatants: list[Combatant] = []
    pc_combatants = [
        Combatant(
            p.name,
            p.ac,
            p.hp,
            [dump_model(a) for a in p.attacks],
            "party",
            getattr(p, "dex_mod", 0),
            max_hp=p.max_hp,
        )
        for p in pcs
    ]
    for c, p in zip(pc_combatants, pcs):
        c.str_mod = getattr(p, "str_mod", 0)
    # Roll initiative for PCs first so they consume the earliest RNG values
    for c in pc_combatants:
        init_seed = rng.randint(0, 10_000_000)
        c.init = roll(f"1d20+{getattr(c, 'dex_mod', 0)}", seed=init_seed)["total"] + 1000
    combatants.extend(pc_combatants)

    # Then add monsters, consuming further RNG values for their HP and initiative
    for m in monsters:
        c = Combatant(m.name, int(m.ac.split()[0]), 0, [], "monsters", (m.dex - 10) // 2)
        c.str_mod = (m.str - 10) // 2
        hp_str = m.hp
        if "(" in hp_str and ")" in hp_str:
            expr = hp_str.split("(")[1].split(")")[0]
            hp_seed = rng.randint(0, 10_000_000)
            c.hp = roll(expr, seed=hp_seed)["total"]
        else:
            c.hp = int(hp_str.split()[0])
        c.attacks = [
            {"name": a.name, "to_hit": a.attack_bonus, "damage_dice": a.damage_dice, "type": a.type}
            for a in m.actions_struct
        ]
        init_seed = rng.randint(0, 10_000_000)
        c.init = roll(f"1d20+{getattr(c, 'dex_mod', 0)}", seed=init_seed)["total"]
        combatants.append(c)

    combatants.sort(key=lambda c: c.init, reverse=True)

    action_state: dict[str, ActionState] = defaultdict(ActionState)
    condition_state: dict[str, ConditionFlags] = {c.name: ConditionFlags() for c in combatants}
    for c in combatants:
        action_state[c.name]

    round_num = 1
    turn = 0
    while round_num <= max_rounds:
        winner = _check_victory(combatants)
        if winner:
            print(f"{winner.capitalize()} win!")
            break
        actor = combatants[turn]
        clear_dodge(action_state[actor.name])
        if actor.defeated:
            turn = (turn + 1) % len(combatants)
            if turn == 0:
                round_num += 1
            continue
        if actor.hp <= 0:
            if getattr(actor, "stable", False):
                turn = (turn + 1) % len(combatants)
                if turn == 0:
                    round_num += 1
                continue
            ds_seed = rng.randint(0, 10_000_000)
            ds = checks.roll_check(0, 10, seed=ds_seed)
            print(
                f"{actor.name} death save {'success' if ds['success'] else 'failure'} ({ds['roll']})"
            )
            roll_val = ds["roll"]
            if roll_val == 20:
                actor.hp = 1
                actor.downed = False
                actor.stable = False
                actor.death_successes = 0
                actor.death_failures = 0
                print(f"{actor.name} regains 1 HP and stands")
            elif roll_val == 1:
                actor.death_failures += 2
            elif ds["success"]:
                actor.death_successes += 1
            else:
                actor.death_failures += 1
            if actor.death_successes >= 3:
                actor.stable = True
                print(f"{actor.name} is stable")
            elif actor.death_failures >= 3:
                actor.defeated = True
                print(f"{actor.name} dies")
            turn = (turn + 1) % len(combatants)
            if turn == 0:
                round_num += 1
            continue
        if actor.side == "party":
            # --- Command input logic ---
            # player prompt: read from --script if provided, else from stdin
            cmd = input_fn("> ")
            cmd_norm = _normalize_cmd(cmd or "")
            parts = shlex.split(cmd_norm) if cmd_norm else []

            def _find_pc(name: str):
                return next((c for c in combatants if c.side == "party" and c.name == name), None)

            def _find_any(name: str):
                return next((c for c in combatants if c.name == name), None)

            # Execute a spell by name and target spec ("all" or a single target name)
            def _do_cast(spell_name: str, target_spec: str = "all") -> None:
                atk = next((a for a in actor.attacks if a["name"] == spell_name), None)
                if not atk:
                    print("Unknown spell")
                    return
                enemies = [c for c in combatants if c.side != actor.side and not c.defeated]
                if target_spec != "all":
                    enemies = [c for c in enemies if c.name == target_spec]
                if not enemies:
                    print("No targets")
                    return

                # roll damage up front (same total per target)
                dmg_seed = rng.randint(0, 10_000_000)
                dmg_total = checks.damage_roll(atk.get("damage_dice", "0"), dmg_seed)["total"]

                # decide model: save-based vs attack-roll
                save_ability = atk.get("save_ability")
                save_dc = atk.get("save_dc")
                use_save = bool(save_ability or save_dc)

                if use_save:
                    ability = (save_ability or getattr(actor, "save_ability", None) or "dex").lower()
                    dc = save_dc if save_dc is not None else 8 + getattr(actor, "proficiency", 0) + getattr(actor, f"{ability}_mod", 0)
                    for tgt in enemies:
                        save_seed = rng.randint(0, 10_000_000)
                        t_mod = getattr(tgt, f"{ability}_mod", 0)
                        save = checks.saving_throw(dc, t_mod, seed=save_seed)
                        print(f"{tgt.name} {ability.upper()} save {'succeeds' if save['success'] else 'fails'}")
                        taken = dmg_total if not save["success"] else dmg_total // 2
                        print(f"{actor.name}'s {atk['name']} hits {tgt.name} for {taken}")
                        _apply_damage(tgt, taken, atk.get("type", "spell"))
                    return

                # attack-roll path (e.g., Fire Bolt)
                casting_ability = (atk.get("attack_ability")
                                   or atk.get("casting_ability")
                                   or getattr(actor, "spell_ability", "int"))
                attack_bonus = atk.get("attack_bonus") if "attack_bonus" in atk else atk.get("to_hit")
                if attack_bonus is None:
                    attack_bonus = getattr(actor, "proficiency", 0) + getattr(actor, f"{casting_ability}_mod", 0)

                for tgt in enemies:
                    ac = getattr(tgt, "ac", 10)
                    tohit_seed = rng.randint(0, 10_000_000)
                    try:
                        ar = checks.attack_roll(attack_bonus, ac, seed=tohit_seed)  # new signature
                        total = (ar.get("detail") or {}).get("total", ar.get("total", ar.get("roll")))
                        hit = ar.get("hit", (total is not None and total >= ac))
                    except TypeError:
                        ar = checks.attack_roll(attack_bonus, seed=tohit_seed)      # old signature
                        total = (ar.get("detail") or {}).get("total", ar.get("total", ar.get("roll")))
                        hit = (total is not None and total >= ac)
                    if total is None:
                        total = attack_bonus
                    print(f"{actor.name} casts {atk['name']} at {tgt.name}: {total} vs AC {ac} → {'hits' if hit else 'misses'}")
                    if hit:
                        _apply_damage(tgt, dmg_total, atk.get("type", "spell"))

            # --- verb handling ---
            if not parts:
                pass
            elif parts[0].lower() in ("q", "quit", "exit"):
                return finalize_result(_check_victory(combatants) or "monsters", combatants, rounds=round_num)
            elif parts[0].lower() in ("end", "e"):
                pass  # loop advances at bottom
            elif parts[0].lower() in ("status", "s", "hp"):
                _print_status(round_num, combatants, action_state, condition_state)
            elif parts[0].lower() in ("actions", "list"):
                for a in actor.attacks or []:
                    print(a.get("name", ""))
            elif parts[0].lower() == "dodge":
                apply_dodge(action_state[actor.name])
                print(f"{actor.name} takes the Dodge action")
            elif parts[0].lower() == "help" and len(parts) >= 2:
                ally = _find_any(parts[1])
                if not ally:
                    print("Unknown target")
                else:
                    apply_help(action_state[actor.name], action_state[ally.name])
                    print(f"{actor.name} helps {ally.name}")
            elif parts[0].lower() == "hide":
                apply_hide(action_state[actor.name])
                print(f"{actor.name} hides")
            elif parts[0].lower() == "stabilize" and len(parts) >= 2:
                tgt = _find_any(parts[1])
                if not tgt:
                    print("Unknown target")
                elif getattr(tgt, "defeated", False):
                    print(f"{tgt.name} is dead.")
                elif getattr(tgt, "hp", 1) > 0:
                    print("Cannot stabilize")
                else:
                    tgt.stable = True
                    tgt.downed = True
                    print(f"{tgt.name} is stable")
            elif parts[0].lower() == "heal" and len(parts) >= 3:
                tgt = _find_any(parts[1])
                if not tgt:
                    print("Unknown target")
                elif getattr(tgt, "defeated", False):
                    print(f"{tgt.name} is dead.")
                else:
                    try:
                        amt = int(parts[2])
                    except ValueError:
                        print("Usage: heal <target> <amount>")
                    else:
                        heal_target(tgt, amt)
            elif cmd_norm.lower().startswith('use "potion of healing" on '):
                m = re.match(r'^use\s+"([^"]+)"\s+on\s+(.+)$', cmd_norm, re.I)
                if not m:
                    print("Unknown command")
                else:
                    item, who = m.groups()
                    tgt = _find_any(who)
                    if not tgt:
                        print("Unknown target")
                    elif getattr(tgt, "defeated", False):
                        print(f"{tgt.name} is dead.")
                    else:
                        heal_seed = rng.randint(0, 10_000_000)
                        rolled = checks.damage_roll("2d4+2", heal_seed)["total"]
                        print(f'Potion of Healing on {tgt.name}: rolled 2d4+2 = {rolled}')
                        heal_target(tgt, rolled)
            elif parts[0].lower() == "shove" and len(parts) >= 3:
                who, mode = parts[1], parts[2].lower()
                tgt = _find_any(who)
                if not tgt:
                    print("Unknown target")
                else:
                    if mode == "prone":
                        condition_state[tgt.name].prone = True
                        print(f"{tgt.name} is knocked prone")
                    else:
                        print("Unknown command")
            elif parts[0].lower() == "stand":
                if getattr(condition_state[actor.name], "prone", False):
                    condition_state[actor.name].prone = False
                print(f"{actor.name} stands")
            elif CAST_RE.match(cmd_norm):
                spell, target, lvl = CAST_RE.match(cmd_norm).groups()
                _do_cast(spell, target or "all")
            elif parts[0].lower() in ("cast", "c") and len(parts) >= 2:
                spell_name = parts[1]
                target_spec = parts[2] if len(parts) >= 3 else "all"
                _do_cast(spell_name, target_spec)
            elif parts[0].lower() in ("a", "attack"):
                who = actor.name
                idx = 1
                if len(parts) >= 4 and _find_pc(parts[1]):  # explicit actor form
                    who = parts[1]
                    idx = 2
                    if who != actor.name:
                        ref = _find_pc(who)
                        if ref and getattr(ref, "hp", 1) <= 0:
                            print(f"{ref.name} is at 0 HP and cannot act")
                        else:
                            print(f"It's {actor.name}'s turn.")
                        who = None  # do not execute an attack
                if who:
                    if len(parts) >= idx + 2:
                        target_name = parts[idx]
                        attack_name = " ".join(parts[idx + 1 :])
                        tgt = _find_any(target_name)
                        if not tgt:
                            print("Unknown target")
                        else:
                            attack = next(
                                (a for a in actor.attacks if a["name"] == attack_name),
                                None,
                            )
                            if not attack:
                                print("Unknown attack")
                            else:
                                action_adv = derive_attack_advantage(
                                    action_state[actor.name], action_state[tgt.name]
                                )
                                cond_adv = derive_condition_advantage(
                                    condition_state[actor.name],
                                    condition_state[tgt.name],
                                    melee=attack.get("type", "melee") != "ranged",
                                )
                                if tgt.hp <= 0:
                                    cond_adv = combine_adv(
                                        cond_adv,
                                        "adv" if attack.get("type", "melee") != "ranged" else "dis",
                                    )
                                adv_mode = combine_adv(action_adv, cond_adv)
                                hit_seed = rng.randint(0, 10_000_000)
                                atk_res = roll(
                                    f"1d20+{attack['to_hit']}",
                                    seed=hit_seed,
                                    adv=adv_mode == "adv",
                                    disadv=adv_mode == "dis",
                                )
                                if os.getenv("GB_TESTING"):
                                    print(f"[dbg] adv_mode={adv_mode}")
                                hit = atk_res["total"] >= tgt.ac
                                roll_val = atk_res["detail"].get("chosen", atk_res["detail"].get("rolls", [0])[0])
                                crit = roll_val == 20
                                if hit:
                                    dmg_seed = rng.randint(0, 10_000_000)
                                    dmg = checks.damage_roll(attack["damage_dice"], dmg_seed)
                                    print(f"{actor.name} hits {tgt.name} for {dmg['total']}")
                                    pre_downed = tgt.hp <= 0
                                    _apply_damage(target, dmg["total"], attack.get("type", "melee"), crit)
                                    if pre_downed and target.hp <= 0 and not target.defeated:
                                        rng.randint(0, 10_000_000)
                                else:
                                    print(f"{actor.name} misses {tgt.name}")
        else:
            enemies = [
                c
                for c in combatants
                if c.side != actor.side
                and not c.defeated
                and not (c.hp <= 0 and getattr(c, "stable", False))
            ]
            if enemies and actor.attacks:
                if any(e.hp <= 0 and e.death_successes > e.death_failures for e in enemies):
                    rng.randint(0, 10_000_000)
                target = choose_target(actor, enemies)
                attack = actor.attacks[0]
                action_adv = derive_attack_advantage(
                    action_state[actor.name], action_state[target.name]
                )
                cond_adv = derive_condition_advantage(
                    condition_state[actor.name],
                    condition_state[target.name],
                    melee=attack.get("type", "melee") != "ranged",
                )
                if target.hp <= 0:
                    cond_adv = combine_adv(
                        cond_adv,
                        "adv" if attack.get("type", "melee") != "ranged" else "dis",
                    )
                adv_mode = combine_adv(action_adv, cond_adv)
                hit_seed = rng.randint(0, 10_000_000)
                atk_res = roll(
                    f"1d20+{attack['to_hit']}",
                    seed=hit_seed,
                    adv=adv_mode == "adv",
                    disadv=adv_mode == "dis",
                )
                if os.getenv("GB_TESTING"):
                    print(f"[dbg] adv_mode={adv_mode}")
                hit = atk_res["total"] >= target.ac
                roll_val = atk_res["detail"].get("chosen", atk_res["detail"].get("rolls", [0])[0])
                crit = roll_val == 20
                if hit:
                    dmg_seed = rng.randint(0, 10_000_000)
                    dmg = checks.damage_roll(attack["damage_dice"], dmg_seed)
                    print(f"{actor.name} hits {target.name} for {dmg['total']}")
                    pre_downed = target.hp <= 0
                    _apply_damage(target, dmg["total"], attack.get("type", "melee"), crit)
                    if pre_downed and target.hp <= 0 and not target.defeated:
                        rng.randint(0, 10_000_000)
                else:
                    print(f"{actor.name} misses {target.name}")
        turn = (turn + 1) % len(combatants)
        if turn == 0:
            round_num += 1
    return finalize_result(_check_victory(combatants) or "monsters", combatants, rounds=round_num)


def run_campaign_cli(path: str | Path, *, start: str | None = None, seed: int | None = None, save: str | None = None, resume: str | None = None, max_rounds: int = 20) -> dict | None:
    """Run a minimal campaign for testing or CLI use.

    The function prints narrative text and handles encounters, checks and
    simple branching choices. When ``save`` is provided, a ``SessionLogger``
    writes accompanying ``.jsonl`` and ``.md`` logs beside the save file.
    Choices are read from ``stdin`` when not attached to a TTY so tests can
    feed scripted input.
    """

    camp = campaign_engine.load_campaign(path)
    base = Path(path).parent if Path(path).is_file() else Path(path)
    pcs = campaign_engine.load_party(camp, base)
    if not pcs:
        raise RuntimeError("No PCs were loaded")
    if resume:
        data = json.loads(Path(resume).read_text())
        start = data.get("scene", start or camp.start)
        hp = data.get("hp", {})
        for pc in pcs:
            if pc.name in hp:
                pc.hp = hp[pc.name]

    logger = SessionLogger(save) if save else None
    current = start or camp.start
    rng = random.Random(seed or camp.seed)
    seen: set[str] = set()
    input_iter = None

    while current:
        scene = camp.scenes[current]
        print(scene.text)
        if logger:
            logger.log_event("narration", text=scene.text)
        if scene.rest:
            if scene.rest.lower().startswith("short"):
                rests.apply_short_rest(pcs, rng)
            else:
                rests.apply_long_rest(pcs)
            current = scene.on_victory or scene.on_defeat
        elif scene.encounter:
            if not pcs:
                raise RuntimeError("Encounter requires PCs")
            enemy_spec = scene.encounter
            enemy_name = ""
            if isinstance(enemy_spec, dict) and "random" in enemy_spec:
                opts = enemy_spec["random"]
                enemy_name = select_monster(
                    tags=opts.get("tags"),
                    cr=opts.get("cr"),
                    exclude=seen if opts.get("exclude_seen") else set(),
                    seed=seed,
                )
                if opts.get("exclude_seen"):
                    seen.add(enemy_name.lower())
            else:
                enemy_name = str(enemy_spec)
            res = campaign_engine.run_encounter(pcs, enemy_name, seed=seed, max_rounds=max_rounds)
            if logger:
                logger.log_event(
                    "encounter",
                    enemy=enemy_name,
                    result=res.get("result"),
                    summary=res.get("summary", ""),
                )
            hp_map = res.get("hp", {})
            for pc in pcs:
                if pc.name in hp_map:
                    pc.hp = hp_map[pc.name]
            current = scene.on_victory if res.get("result") == "victory" else scene.on_defeat
        elif scene.check:
            roll_res = checks.roll_check(0, scene.check.dc, advantage=scene.check.advantage, seed=seed)
            if logger:
                logger.log_event(
                    "check",
                    ability=scene.check.ability,
                    skill=scene.check.skill,
                    dc=scene.check.dc,
                    success=roll_res["success"],
                    roll=roll_res["roll"],
                    total=roll_res["total"],
                )
            current = scene.check.on_success if roll_res["success"] else scene.check.on_failure
        elif scene.choices:
            for idx, choice in enumerate(scene.choices, 1):
                print(f"{idx}. {choice.text}")
            if input_iter is None and not sys.stdin.isatty():
                input_iter = iter([line.rstrip("\n") for line in sys.stdin])
            if input_iter:
                try:
                    choice_line = next(input_iter)
                    print(f"> {choice_line}")
                except StopIteration:
                    break
            else:
                choice_line = input("> ")
            try:
                idx = int(choice_line.strip())
            except ValueError:
                idx = 1
            idx = max(1, min(idx, len(scene.choices)))
            chosen = scene.choices[idx - 1]
            if logger:
                logger.log_event("choice", choice=idx, next=chosen.next)
            current = chosen.next
        else:
            break
    if save:
        Path(save).write_text(json.dumps({"hp": {pc.name: pc.hp for pc in pcs}, "scene": current}))
    return {"hp": {pc.name: pc.hp for pc in pcs}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Grimbrain CLI")
    parser.add_argument("--play", action="store_true", help="Run combat simulator")
    parser.add_argument("--campaign", help="Path to campaign directory or YAML", default=None)
    parser.add_argument("--start", help="Starting scene for campaign", default=None)
    parser.add_argument("--pc", help="Path to party JSON file", default=None)
    parser.add_argument("--encounter", help="Monster spec for play mode", default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--max-rounds", type=int, default=20)
    parser.add_argument("--packs", help="Comma-separated pack names or paths", default=None)
    parser.add_argument("--autosave", action="store_true", help="Autosave play log")
    parser.add_argument("--save", help="Path to save campaign state", default=None)
    parser.add_argument("--resume", help="Resume state JSON", default=None)
    parser.add_argument("--pc-wizard", action="store_true", help="Create party JSON interactively or from preset")
    parser.add_argument("--preset", help="Preset name for pc-wizard", default=None)
    parser.add_argument("--out", help="Output path for pc-wizard", default=None)
    parser.add_argument("--script", type=argparse.FileType("r"),
                        help="Path to a text file of commands to feed into the in-combat CLI")

    args = parser.parse_args()

    if args.pc_wizard:
        pc_wizard.main(out=args.out, preset=args.preset)
    elif args.resume and not args.campaign and not args.play:
        sess = Session.load(args.resume)
        print(f"Resumed scene '{sess.scene}' with {len(sess.steps)} steps")
    elif args.play:
        camp = None
        base = None
        if args.campaign:
            camp = campaign_engine.load_campaign(args.campaign)
            base = Path(args.campaign).parent if Path(args.campaign).is_file() else Path(args.campaign)
        if args.pc:
            pcs = load_party_file(Path(args.pc))
        elif camp:
            pcs = campaign_engine.load_party(camp, base)
        else:
            raise SystemExit("--pc is required for play mode")

        packs = load_packs(args.packs.split(",")) if args.packs else {}

        def _lookup(name: str) -> MonsterSidecar:
            data = packs.get(name.lower()) if packs else None
            if data:
                return MonsterSidecar(**data)
            return _lookup_fallback(name)

        encounter_spec = args.encounter
        if encounter_spec is None:
            if camp is None:
                raise SystemExit("--encounter is required for play mode")
            scene_id = args.start or camp.start
            # --- PATCH START ---
            # Walk forward through choices until we find a scene with an encounter
            visited = set()
            while True:
                scene = camp.scenes.get(scene_id)
                if not scene:
                    raise SystemExit(f"Scene '{scene_id}' not found in campaign.")
                if getattr(scene, "encounter", None):
                    encounter_spec = scene.encounter
                    break
                visited.add(scene_id)
                # Try to follow the first choice, if any
                if getattr(scene, "choices", None) and scene.choices:
                    # Support both dict and object style
                    next_id = getattr(scene.choices[0], "goto", None) or getattr(scene.choices[0], "next", None)
                    if not next_id or next_id in visited:
                        encounter_spec = None
                        break
                    scene_id = next_id
                else:
                    encounter_spec = None
                    break
            # --- PATCH END ---
        print(f"DEBUG: Encounter spec loaded: {encounter_spec}")  # <--- Add this line
        if isinstance(encounter_spec, dict) and "random" in encounter_spec:
            opts = encounter_spec["random"]
            encounter_spec = select_monster(
                tags=opts.get("tags"), cr=opts.get("cr"), seed=args.seed
            )
        monsters = parse_monster_spec(str(encounter_spec), _lookup)
        monsters = [m for m in monsters if m is not None]
        if not monsters:
            print(f"ERROR: No valid monsters loaded from encounter spec: {encounter_spec}")
            sys.exit(1)
        play_cli(
            pcs,
            monsters,
            seed=args.seed,
            max_rounds=args.max_rounds,
            autosave=args.autosave,
            script=args.script,  # <-- pass the script argument
        )
    elif args.campaign:
        run_campaign_cli(
            args.campaign,
            start=args.start,
            seed=args.seed,
            save=args.save,
            resume=args.resume,
            max_rounds=args.max_rounds,
        )
    else:
        parser.print_help()
