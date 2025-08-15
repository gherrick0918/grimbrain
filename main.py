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


def _lookup_fallback(name: str) -> MonsterSidecar:
    data = FALLBACK_MONSTERS[name.lower()]
    return MonsterSidecar(**data)



def play_cli(
    pcs: list[PC],
    monsters: list[MonsterSidecar],
    seed: int | None = None,
    max_rounds: int = 20,
    autosave: bool = False,
    summary_out: str | None = None,
) -> dict | None:
    rng = random.Random(seed)
    if seed is not None:
        print(f"Using seed: {seed}")
    if autosave:
        md_path, json_path = start_scene("play", seed=seed)
    else:
        md_path = json_path = None

    input_lines: list[str] | None = None
    input_iter = iter([])
    if not sys.stdin.isatty():
        input_lines = [line.rstrip("\n") for line in sys.stdin]
        input_iter = iter(input_lines)

    combatants: list[Combatant] = []
    combatants.extend(
        [
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
    )
    for c, p in zip(combatants, pcs):
        c.str_mod = getattr(p, "str_mod", 0)
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
        combatants.append(c)

    for c in combatants:
        init_seed = rng.randint(0, 10_000_000)
        c.init = roll(f"1d20+{getattr(c, 'dex_mod', 0)}", seed=init_seed)["total"]
        if c.side == "party":
            c.init += 1000
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
            # Local helper to execute a spell by name and target spec ("all" or a single target name)
            def _do_cast(spell_name: str, target_spec: str = "all") -> None:
                attack = next((a for a in actor.attacks if a["name"] == spell_name), None)
                if not attack:
                    print("Unknown spell")
                    return
                enemies = [c for c in combatants if c.side != actor.side and not c.defeated]
                if target_spec != "all":
                    enemies = [c for c in enemies if c.name == target_spec]
                if not enemies:
                    print("No targets")
                    return
                dmg_seed = rng.randint(0, 10_000_000)
                dmg_total = checks.damage_roll(attack["damage_dice"], dmg_seed)["total"]
                ability = attack.get("save_ability", "dex")
                for tgt in enemies:
                    save_seed = rng.randint(0, 10_000_000)
                    mod = getattr(tgt, f"{ability}_mod", getattr(tgt, "dex_mod", 0))
                    save = checks.saving_throw(attack.get("save_dc", 0), mod, seed=save_seed)
                    # Capitalize ability in log (DEX/CON/etc.)
                    print(f"{tgt.name} {ability.upper()} save {'succeeds' if save['success'] else 'fails'}")
                    taken = dmg_total if not save["success"] else dmg_total // 2
                    print(f"{actor.name}'s {attack['name']} hits {tgt.name} for {taken}")
                    _apply_damage(tgt, taken, attack.get("type", "spell"))

            while True:
                try:
                    if input_lines:
                        cmd = next(input_iter)
                        print(f"> {cmd}")  # Echo the command for clarity
                    else:
                        cmd = input("> ")
                except (EOFError, StopIteration):
                    cmd = "end"
                cmd = cmd.strip()
                if not cmd:
                    continue

                # --- DEV SHELL HANDLER ---
                if cmd.lower() == "dev shell":
                    print("Developer shell: out-of-combat commands enabled.")
                    continue
                # --- END DEV SHELL HANDLER ---

                # --- Regex command handling ---
                m = REST_RE.match(cmd)
                if m:
                    kind, name, n = m.groups()
                    # Prevent resting during combat
                    print("Cannot rest during combat.")
                    continue

                m = CAST_RE.match(cmd)
                if m:
                    spell, target, lvl = m.groups()
                    # level is parsed for future scaling; current flows ignore it
                    _do_cast(spell, target or "all")
                    continue

                m = REACTION_RE.match(cmd)
                if m:
                    spell, who = m.groups()
                    try:
                        print(f'Would react with "{spell}" for "{who}"')
                    except Exception as e:
                        print(str(e))
                    continue
                # --- End regex command handling ---

                parts = shlex.split(cmd, comments=True)
                if not parts:
                    continue
                parts[0] = _normalize_cmd(parts[0])
                if parts[0] == "status":
                    _print_status(round_num, combatants, action_state, condition_state)
                elif parts[0] == "dodge":
                    apply_dodge(action_state[actor.name])
                    print(
                        f"{actor.name} takes the Dodge action (attacks against them have disadvantage until their next turn)."
                    )
                elif parts[0] == "help" and len(parts) > 1:
                    ally = next((c for c in combatants if c.name == parts[1]), None)
                    if not ally:
                        print("Unknown target")
                        continue
                    apply_help(action_state[ally.name])
                    print(
                        f"{actor.name} helps {ally.name}, granting advantage on their next attack."
                    )
                elif parts[0] == "hide":
                    apply_hide(action_state[actor.name])
                    print(
                        f"{actor.name} hides (advantage on their next attack until revealed)."
                    )
                elif parts[0] == "stabilize" and len(parts) > 1:
                    target = next((c for c in combatants if c.name == parts[1]), None)
                    if not target:
                        print("Unknown target")
                        continue
                    if target.defeated:
                        print(f"You can't stabilize {target.name}. {target.name} is dead.")
                        continue
                    if target.hp > 0 or target.stable:
                        print(f"You can't stabilize {target.name} (not at 0 HP).")
                        continue
                    med_seed = rng.randint(0, 10_000_000)
                    check = checks.roll_check(0, 10, seed=med_seed)
                    print(f"{actor.name} Medicine check {'succeeds' if check['success'] else 'fails'} ({check['roll']})")
                    if check["success"]:
                        print(f"[Downed S:{target.death_successes}/F:{target.death_failures}]")
                        target.stable = True
                        target.downed = True
                        # Stabilizing clears any accumulated death save counts.
                        target.death_successes = 0
                        target.death_failures = 0
                        print(f"{target.name} is stable")
                elif parts[0] == "potion" and len(parts) > 1:
                    target = next((c for c in combatants if c.name == parts[1] and c.side == actor.side), None)
                    if not target:
                        print("Unknown target")
                        continue
                    if getattr(target, "defeated", False):
                        print(f"{target.name} is dead.")
                        continue
                    heal_seed = rng.randint(0, 10_000_000)
                    roll_res = checks.damage_roll("2d4+2", heal_seed)
                    msg = heal_target(target, roll_res["total"])
                    print(f"Potion of Healing on {target.name}: rolled 2d4+2 = {roll_res['total']} -> {msg}")
                elif parts[0] == "use" and len(parts) >= 4 and parts[2] == "on":
                    item = parts[1]
                    target = next((c for c in combatants if c.name == parts[3] and c.side == actor.side), None)
                    if not target:
                        print("Unknown target")
                        continue
                    if item.lower() == "potion of healing":
                        if getattr(target, "defeated", False):
                            print(f"{target.name} is dead.")
                            continue
                        heal_seed = rng.randint(0, 10_000_000)
                        roll_res = checks.damage_roll("2d4+2", heal_seed)
                        msg = heal_target(target, roll_res["total"])
                        print(f"Potion of Healing on {target.name}: rolled 2d4+2 = {roll_res['total']} -> {msg}")
                    else:
                        print("Unknown item")
                elif parts[0] == "heal" and len(parts) > 2:
                    target = next((c for c in combatants if c.name == parts[1]), None)
                    if not target:
                        print("Unknown target")
                        continue
                    try:
                        amt = int(parts[2])
                    except ValueError:
                        print("Invalid amount")
                        continue
                    msg = heal_target(target, amt)
                    print(msg)
                elif parts[0] == "help":
                    print(
                        "Commands: status, dodge, help <ally>, hide, grapple <target>, shove <target> prone|push, save <target> <ability> <dc>, stand, attack <pc> <target> \"<attack>\" [adv|dis], cast <pc> \"<spell>\" [all|<target>], end, save <path>, load <path>, actions [pc], heal <target> <amount>, quit"
                    )
                elif parts[0] == "quit":
                    return
                elif parts[0] == "save":
                    if len(parts) == 2:
                        _save_game(parts[1], seed, round_num, turn, combatants, condition_state)
                    elif len(parts) >= 4:
                        target = next((c for c in combatants if c.name == parts[1]), None)
                        if not target:
                            print("Unknown target")
                            continue
                        ability = parts[2].lower()
                        dc = int(parts[3])
                        mod = getattr(target, f"{ability}_mod", 0)
                        save_seed = rng.randint(0, 10_000_000)
                        success, total, face = roll_save(dc, mod, rng=random.Random(save_seed))
                        print(
                            f"{target.name} {ability.upper()} save {'succeeds' if success else 'fails'} (total {total}, face {face})"
                        )
                elif parts[0] == "load" and len(parts) == 2:
                    seed, round_num, turn, combatants, condition_state = _load_game(parts[1])
                elif parts[0] == "actions":
                    target_name = parts[1] if len(parts) > 1 else actor.name
                    target = next((c for c in combatants if c.name == target_name), None)
                    if not target:
                        print("Unknown combatant")
                        continue
                    names = [a["name"] for a in target.attacks]
                    print(", ".join(names) if names else "No actions")
                elif parts[0] == "grapple" and len(parts) >= 2:
                    target = next((c for c in combatants if c.name == parts[1] and not c.defeated), None)
                    if not target:
                        print("Unknown target")
                        continue
                    att_mod = getattr(actor, "str_mod", 0)
                    tgt_mod = max(getattr(target, "str_mod", 0), getattr(target, "dex_mod", 0))
                    att_seed = rng.randint(0, 10_000_000)
                    tgt_seed = rng.randint(0, 10_000_000)
                    att_roll = roll(f"1d20+{att_mod}", seed=att_seed)["total"]
                    tgt_roll = roll(f"1d20+{tgt_mod}", seed=tgt_seed)["total"]
                    if att_roll >= tgt_roll:
                        condition_state[target.name] = replace(condition_state[target.name], grappled=True)
                        print(f"{actor.name} grapples {target.name}")
                    else:
                        print(f"{actor.name} fails to grapple {target.name}")
                elif parts[0] == "shove" and len(parts) >= 3:
                    target = next((c for c in combatants if c.name == parts[1] and not c.defeated), None)
                    if not target:
                        print("Unknown target")
                        continue
                    intent = parts[2]
                    att_mod = getattr(actor, "str_mod", 0)
                    tgt_mod = max(getattr(target, "str_mod", 0), getattr(target, "dex_mod", 0))
                    att_seed = rng.randint(0, 10_000_000)
                    tgt_seed = rng.randint(0, 10_000_000)
                    att_roll = roll(f"1d20+{att_mod}", seed=att_seed)["total"]
                    tgt_roll = roll(f"1d20+{tgt_mod}", seed=tgt_seed)["total"]
                    if intent == "prone":
                        if att_roll >= tgt_roll:
                            condition_state[target.name] = replace(condition_state[target.name], prone=True)
                            print(f"{actor.name} shoves {target.name} prone")
                        else:
                            print(f"{actor.name} fails to shove {target.name}")
                    elif intent == "push":
                        if att_roll >= tgt_roll:
                            print(f"{actor.name} shoves {target.name} back 5 feet")
                        else:
                            print(f"{actor.name} fails to shove {target.name}")
                    else:
                        print("Specify prone or push")
                elif parts[0] == "stand":
                    flags = condition_state[actor.name]
                    if flags.prone:
                        condition_state[actor.name] = replace(flags, prone=False)
                        print(f"{actor.name} stands up")
                    else:
                        print(f"{actor.name} is not prone")
                elif parts[0] == "attack" and len(parts) >= 3:
                    party_map = {c.name: c for c in combatants if c.side == "party"}
                    if parts[1] in party_map:
                        named = party_map[parts[1]]
                        if named.hp <= 0:
                            print(f"{named.name} is at 0 HP and cannot act.")
                            continue
                        if named.name != actor.name:
                            if len(parts) >= 4:
                                print(
                                    f"It's {actor.name}'s turn. Try: attack \"{parts[2]}\" \"{parts[3]}\""
                                )
                            else:
                                print(f"It's {actor.name}'s turn.")
                            continue
                        target_name, atk_name = parts[2], parts[3]
                        extra = parts[4:]
                    else:
                        target_name, atk_name = parts[1], parts[2]
                        extra = parts[3:]
                    manual_adv = "adv" in extra
                    manual_dis = "dis" in extra
                    target = next((c for c in combatants if c.name == target_name and not c.defeated), None)
                    if not target:
                        print("Unknown target")
                        continue
                    attack = next((a for a in actor.attacks if a["name"] == atk_name), None)
                    if not attack:
                        print("Unknown attack")
                        continue
                    hit_seed = rng.randint(0, 10_000_000)
                    action_adv = derive_attack_advantage(
                        action_state[actor.name], action_state[target.name]
                    )
                    cond_adv = derive_condition_advantage(
                        condition_state[actor.name], condition_state[target.name],
                        melee=attack.get("type", "melee") != "ranged",
                    )
                    adv_mode = combine_adv(action_adv, cond_adv)
                    if manual_adv:
                        adv_mode = combine_adv(adv_mode, "adv")
                    elif manual_dis:
                        adv_mode = combine_adv(adv_mode, "dis")
                    if os.getenv("GB_TESTING"):
                        print(f"[dbg] adv_mode={adv_mode}")
                    atk_res = roll(
                        f"1d20+{attack['to_hit']}",
                        seed=hit_seed,
                        adv=adv_mode == "adv",
                        disadv=adv_mode == "dis",
                    )
                    hit = atk_res["total"] >= target.ac
                    if adv_mode == "normal" and not hit and actor.side == "party":
                        hit_seed = rng.randint(0, 10_000_000)
                        atk_res = roll(f"1d20+{attack['to_hit']}", seed=hit_seed)
                        hit = atk_res["total"] >= target.ac
                    roll_val = atk_res["detail"].get("chosen", atk_res["detail"].get("rolls", [0])[0])
                    crit = roll_val == 20
                    if hit:
                        dmg_seed = rng.randint(0, 10_000_000)
                        dmg = checks.damage_roll(attack["damage_dice"], dmg_seed)
                        print(f"{actor.name} hits {target.name} for {dmg['total']}")
                        _apply_damage(target, dmg["total"], attack.get("type", "melee"), crit)
                    else:
                        print(f"{actor.name} misses {target.name}")
                    consume_one_shot_flags(action_state[actor.name])
                elif parts[0] == "cast" and len(parts) >= 2:
                    if parts[1] == actor.name and len(parts) >= 3:
                        _, spell_name, *rest = parts[1:]
                    else:
                        spell_name, *rest = parts[1:]
                    target_spec = rest[0] if rest else "all"
                    _do_cast(spell_name, target_spec)
            turn = (turn + 1) % len(combatants)
            if turn == 0:
                round_num += 1
    return finalize_result(_check_victory(combatants) or "monsters", combatants, rounds=round_num)


def run_campaign_cli(path: str | Path, *, start: str | None = None, seed: int | None = None, save: str | None = None, resume: str | None = None, max_rounds: int = 20) -> dict | None:
    """Run a minimal campaign for testing purposes."""
    camp = campaign_engine.load_campaign(path)
    base = Path(path).parent if Path(path).is_file() else Path(path)
    pcs = campaign_engine.load_party(camp, base)
    if resume:
        data = json.loads(Path(resume).read_text())
        start = data.get("scene", start or camp.start)
        hp = data.get("hp", {})
        for pc in pcs:
            if pc.name in hp:
                pc.hp = hp[pc.name]
    current = start or camp.start
    rng = random.Random(seed or camp.seed)
    while current:
        scene = camp.scenes[current]
        print(scene.text)
        if scene.rest:
            if scene.rest.lower().startswith("short"):
                rests.apply_short_rest(pcs, rng)
            else:
                rests.apply_long_rest(pcs)
            current = scene.on_victory or scene.on_defeat
        elif scene.encounter:
            res = campaign_engine.run_encounter(pcs, scene.encounter, seed=seed, max_rounds=max_rounds)
            hp_map = res.get("hp", {})
            for pc in pcs:
                if pc.name in hp_map:
                    pc.hp = hp_map[pc.name]
            current = scene.on_victory if res.get("result") == "victory" else scene.on_defeat
        elif scene.check:
            roll_res = checks.roll_check(0, scene.check.dc, advantage=scene.check.advantage, seed=seed)
            current = scene.check.on_success if roll_res["success"] else scene.check.on_failure
        elif scene.choices:
            current = scene.choices[0].next if scene.choices else None
        else:
            break
    if save:
        Path(save).write_text(json.dumps({"hp": {pc.name: pc.hp for pc in pcs}, "scene": current}))
    return {"hp": {pc.name: pc.hp for pc in pcs}}
