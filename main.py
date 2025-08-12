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

from grimbrain.engine.session import Session, start_scene, log_step
from grimbrain.engine.combat import (
    run_round,
    run_encounter,
    parse_monster_spec,
    choose_target,
    Combatant,
)
from grimbrain.engine.dice import roll
from grimbrain.engine import checks
from grimbrain.models import PC, MonsterSidecar, dump_model
from grimbrain.campaign import load_party_file
from grimbrain.engine import campaign as campaign_engine
from grimbrain.engine.logger import SessionLogger
from grimbrain.fallback_monsters import FALLBACK_MONSTERS
from grimbrain.engine.encounter import compute_encounter
from grimbrain.content.packs import load_packs

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


def _serialize_combatant(c: Combatant) -> dict:
    return {
        "name": c.name,
        "ac": c.ac,
        "hp": c.hp,
        "side": c.side,
        "dex_mod": getattr(c, "dex_mod", 0),
        "attacks": c.attacks,
        "defeated": c.defeated,
        "init": getattr(c, "init", 0),
    }


def _deserialize_combatants(data: list[dict]) -> list[Combatant]:
    combs: list[Combatant] = []
    for cd in data:
        c = Combatant(cd["name"], cd["ac"], cd["hp"], cd["attacks"], cd["side"], cd.get("dex_mod", 0))
        c.defeated = cd.get("defeated", False)
        c.init = cd.get("init", 0)
        combs.append(c)
    combs.sort(key=lambda c: c.init, reverse=True)
    return combs


def _print_status(round_num: int, combatants: list[Combatant]) -> None:
    print(f"Round {round_num}")
    order = ", ".join(c.name for c in combatants)
    print(f"Initiative: {order}")
    for c in combatants:
        hp = "DEFEATED" if c.defeated else f"{c.hp} HP"
        print(f"{c.name}: {hp}, AC {c.ac}")


def _check_victory(combatants: list[Combatant]) -> str | None:
    party_alive = any(c.side == "party" and not c.defeated for c in combatants)
    monsters_alive = any(c.side == "monsters" and not c.defeated for c in combatants)
    if not party_alive:
        return "monsters"
    if not monsters_alive:
        return "party"
    return None


def _save_game(path: str, seed: int | None, round_num: int, turn: int, combatants: list[Combatant]) -> None:
    sess = Session(scene="play", seed=seed, steps=[{
        "round": round_num,
        "turn": turn,
        "combatants": [_serialize_combatant(c) for c in combatants],
    }])
    sess.save(path)
    print(f"Saved to {path}")


def _load_game(path: str):
    sess = Session.load(path)
    if sess.steps:
        data = sess.steps[0]
        round_num = data.get("round", 1)
        turn = data.get("turn", 0)
        combatants = _deserialize_combatants(data.get("combatants", []))
    else:
        round_num = 1
        turn = 0
        combatants = []
    return sess.seed, round_num, turn, combatants


def _edit_distance_one(a: str, b: str) -> bool:
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1
    if len(a) + 1 == len(b):
        for i in range(len(b)):
            if a[:i] == b[:i] and a[i:] == b[i + 1 :]:
                return True
        return False
    if len(b) + 1 == len(a):
        for i in range(len(a)):
            if a[:i] == b[:i] and a[i + 1 :] == b[i:]:
                return True
        return False
    return False


def _normalize_cmd(cmd: str) -> str:
    aliases = {"a": "attack", "atk": "attack", "c": "cast", "s": "status", "q": "quit"}
    if cmd in aliases:
        return aliases[cmd]
    known = ["attack", "cast", "status", "quit", "end", "save", "load", "actions"]
    for k in known:
        if _edit_distance_one(cmd, k):
            return k
    return cmd


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

    combatants: list[Combatant] = []
    combatants.extend(
        [Combatant(p.name, p.ac, p.hp, [dump_model(a) for a in p.attacks], "party", 0) for p in pcs]
    )
    for m in monsters:
        c = Combatant(m.name, int(m.ac.split()[0]), 0, [], "monsters", (m.dex - 10) // 2)
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
    combatants.sort(key=lambda c: c.init, reverse=True)

    round_num = 1
    turn = 0
    while round_num <= max_rounds:
        winner = _check_victory(combatants)
        if winner:
            print(f"{winner.capitalize()} wins!")
            return
        actor = combatants[turn]
        if actor.defeated:
            turn = (turn + 1) % len(combatants)
            if turn == 0:
                round_num += 1
            continue
        if actor.side == "party":
            while True:
                try:
                    cmd = input("> ").strip()
                except EOFError:
                    cmd = "end"
                if not cmd:
                    continue
                parts = shlex.split(cmd)
                parts[0] = _normalize_cmd(parts[0])
                if parts[0] == "status":
                    _print_status(round_num, combatants)
                elif parts[0] == "help":
                    print(
                        "Commands: status, attack <pc> <target> \"<attack>\" [adv|dis], cast <pc> \"<spell>\" [all|<target>], end, save <path>, load <path>, actions [pc], quit"
                    )
                elif parts[0] == "quit":
                    return
                elif parts[0] == "save":
                    if len(parts) == 2:
                        _save_game(parts[1], seed, round_num, turn, combatants)
                elif parts[0] == "load" and len(parts) == 2:
                    seed, round_num, turn, combatants = _load_game(parts[1])
                elif parts[0] == "actions":
                    target_name = parts[1] if len(parts) > 1 else actor.name
                    target = next((c for c in combatants if c.name == target_name), None)
                    if not target:
                        print("Unknown combatant")
                        continue
                    names = [a["name"] for a in target.attacks]
                    print(", ".join(names) if names else "No actions")
                elif parts[0] == "attack" and len(parts) >= 3:
                    if parts[1] == actor.name and len(parts) >= 4:
                        _, target_name, atk_name = parts[1], parts[2], parts[3]
                        extra = parts[4:]
                    else:
                        target_name, atk_name = parts[1], parts[2]
                        extra = parts[3:]
                    adv = "adv" in extra
                    dis = "dis" in extra
                    target = next((c for c in combatants if c.name == target_name and not c.defeated), None)
                    if not target:
                        print("Unknown target")
                        continue
                    attack = next((a for a in actor.attacks if a["name"] == atk_name), None)
                    if not attack:
                        print("Unknown attack")
                        continue
                    hit_seed = rng.randint(0, 10_000_000)
                    if adv or dis:
                        atk_res = roll(f"1d20+{attack['to_hit']}", seed=hit_seed, adv=adv, disadv=dis)
                        hit = atk_res["total"] >= target.ac
                    else:
                        atk_res = checks.attack_roll(attack["to_hit"], target.ac, hit_seed)
                        hit = atk_res["hit"]
                    if hit:
                        dmg_seed = rng.randint(0, 10_000_000)
                        dmg = checks.damage_roll(attack["damage_dice"], dmg_seed)
                        target.hp -= dmg["total"]
                        print(f"{actor.name} hits {target.name} for {dmg['total']}")
                        if target.hp <= 0:
                            target.defeated = True
                            print(f"{target.name} is defeated")
                    else:
                        print(f"{actor.name} misses {target.name}")
                elif parts[0] == "cast" and len(parts) >= 2:
                    if parts[1] == actor.name and len(parts) >= 3:
                        _, spell_name, *rest = parts[1:]
                    else:
                        spell_name, *rest = parts[1:]
                    target_spec = rest[0] if rest else "all"
                    attack = next((a for a in actor.attacks if a["name"] == spell_name), None)
                    if not attack:
                        print("Unknown spell")
                        continue
                    enemies = [c for c in combatants if c.side != actor.side and not c.defeated]
                    if target_spec != "all":
                        enemies = [c for c in enemies if c.name == target_spec]
                    if not enemies:
                        print("No targets")
                        continue
                    dmg_seed = rng.randint(0, 10_000_000)
                    dmg_total = checks.damage_roll(attack["damage_dice"], dmg_seed)["total"]
                    ability = attack.get("save_ability", "dex")
                    for tgt in enemies:
                        save_seed = rng.randint(0, 10_000_000)
                        mod = getattr(tgt, f"{ability}_mod", getattr(tgt, "dex_mod", 0))
                        save = checks.saving_throw(attack.get("save_dc", 0), mod, seed=save_seed)
                        print(f"{tgt.name} Dex save {'succeeds' if save['success'] else 'fails'}")
                        taken = dmg_total if not save["success"] else dmg_total // 2
                        tgt.hp -= taken
                        print(f"{actor.name}'s {attack['name']} hits {tgt.name} for {taken}")
                        if tgt.hp <= 0:
                            tgt.defeated = True
                            print(f"{tgt.name} is defeated")
                elif parts[0] == "end":
                    break
                else:
                    print("Unknown command")
        else:
            enemies = [c for c in combatants if c.side != actor.side and not c.defeated]
            if enemies and actor.attacks:
                attack = actor.attacks[0]
                target_seed = rng.randint(0, 10_000_000)
                target = choose_target(actor, enemies, seed=target_seed)
                hit_seed = rng.randint(0, 10_000_000)
                atk = checks.attack_roll(attack["to_hit"], target.ac, hit_seed)
                if atk["hit"]:
                    dmg_seed = rng.randint(0, 10_000_000)
                    dmg = checks.damage_roll(attack["damage_dice"], dmg_seed)
                    target.hp -= dmg["total"]
                    print(f"{actor.name} hits {target.name} for {dmg['total']}")
                    if target.hp <= 0:
                        target.defeated = True
                        print(f"{target.name} is defeated")
                else:
                    print(f"{actor.name} misses {target.name}")
            # monsters with no attacks or no targets simply skip their turn
        turn = (turn + 1) % len(combatants)
        hp_line = ", ".join(f"{c.name} {0 if c.defeated else c.hp}" for c in combatants)
        next_name = combatants[turn].name
        print(f"HP: {hp_line}")
        print(f"Next: {next_name}")
        if autosave and md_path and json_path:
            log_step(md_path, json_path, f"Round {round_num} {actor.name}", f"HP: {hp_line}\nNext: {next_name}")
        if turn == 0:
            round_num += 1

    winner = _check_victory(combatants)
    if winner:
        xp = compute_encounter(monsters)
        loot_seed = rng.randint(0, 10_000_000)
        loot = roll(f"{len(monsters)}d6", seed=loot_seed)["total"]
        summary = {
            'winner': winner,
            'rounds': round_num - 1 if turn == 0 else round_num,
            'xp': xp['total_xp'],
            'loot_gp': loot,
        }
        print(
            f"{winner.capitalize()} wins after {summary['rounds']} rounds! XP {summary['xp']}, Loot {summary['loot_gp']} gp",
        )
        if summary_out:
            Path(summary_out).write_text(json.dumps(summary, indent=2))
            print(f"Summary written to {summary_out}")
        if autosave and md_path and json_path:
            log_step(md_path, json_path, 'Summary', json.dumps(summary))
        result = {
            'result': 'victory' if winner == 'party' else 'defeat',
            'summary': summary,
            'hp': {c.name: 0 if c.defeated else c.hp for c in combatants if c.side == 'party'},
        }
        return result
    else:
        print('Max rounds reached')
    return None


def run_campaign_cli(
    path: Path,
    start: str | None = None,
    resume: str | None = None,
    save: str | None = None,
    seed: int | None = None,
    pcs: list[PC] | None = None,
    interactive: bool = False,
    max_rounds: int = 10,
) -> int:
    """Run a text campaign from a YAML file or directory.

    ``path`` may point directly to the ``campaign.yaml`` file or to a directory
    containing it.  ``load_campaign`` accepts either, but loading the party
    requires the directory so that relative ``party_files`` can be resolved.
    Previously we passed the YAML file path straight through which resulted in
    paths like ``campaign.yaml/pc.json`` and crashes when the CLI was invoked
    with ``--campaign`` pointing to a folder.  Normalising the base directory
    here fixes those failures and allows both invocation styles.
    """

    path = Path(path)
    camp = campaign_engine.load_campaign(path)
    base = path if path.is_dir() else path.parent
    if pcs is None:
        pcs = campaign_engine.load_party(camp, base)
    if resume:
        data = json.loads(Path(resume).read_text())
        scene_id = data.get('scene', camp.start)
        hp = data.get('hp', {})
        for pc in pcs:
            if pc.name in hp:
                pc.hp = hp[pc.name]
    else:
        scene_id = start or camp.start
    logger = SessionLogger(Path(save).with_suffix('')) if save else None

    def _save():
        if save:
            state = {'scene': scene_id, 'hp': {pc.name: pc.hp for pc in pcs}}
            Path(save).write_text(json.dumps(state))

    _save()
    while scene_id:
        scene = camp.scenes.get(scene_id)
        if scene is None:
            break
        print(scene.text)
        if logger:
            logger.log_event('narration', scene=scene_id, text=scene.text)
        if scene.encounter:
            if not pcs:
                print(
                    "This scene includes an encounter, but no PCs were loaded. Pass --play --pc <file> or --pc-wizard to create a party.",
                    file=sys.stderr,
                )
                return 2
            if interactive:
                def _lookup(name: str) -> MonsterSidecar:
                    data = FALLBACK_MONSTERS[name.lower()]
                    return MonsterSidecar(**data)

                monsters = parse_monster_spec(scene.encounter, _lookup)
                res = play_cli(pcs, monsters, seed=seed or camp.seed, max_rounds=max_rounds)
                if res is None:
                    res = {
                        'result': 'defeat',
                        'hp': {pc.name: pc.hp for pc in pcs},
                    }
            else:
                res = campaign_engine.run_encounter(
                    pcs,
                    scene.encounter,
                    seed=seed or camp.seed,
                    max_rounds=max_rounds,
                )
            if logger and res:
                logger.log_event('encounter', scene=scene_id, enemy=scene.encounter, **res)
            if res:
                for pc in pcs:
                    if pc.name in res.get('hp', {}):
                        pc.hp = res['hp'][pc.name]
                scene_id = scene.on_victory if res.get('result') == 'victory' else scene.on_defeat
            else:
                scene_id = scene.on_defeat
            _save()
            continue
        if scene.check:
            res = checks.roll_check(
                0,
                scene.check.dc,
                advantage=scene.check.advantage,
                seed=seed or camp.seed,
            )
            if logger:
                log_data = {
                    'scene': scene_id,
                    'dc': scene.check.dc,
                    'roll': res['roll'],
                    'total': res['total'],
                    'success': res['success'],
                }
                if scene.check.ability:
                    log_data['ability'] = scene.check.ability
                if scene.check.skill:
                    log_data['skill'] = scene.check.skill
                logger.log_event('check', **log_data)
            scene_id = scene.check.on_success if res['success'] else scene.check.on_failure
            _save()
            continue
        if not scene.choices:
            break
        for idx, ch in enumerate(scene.choices, start=1):
            print(f"{idx}. {ch.text}")
        try:
            ans = input('> ').strip()
        except EOFError:
            break
        try:
            choice = scene.choices[int(ans) - 1]
        except Exception:
            choice = scene.choices[0]
        if logger:
            logger.log_event('choice', scene=scene_id, choice=choice.text, next=choice.next)
        scene_id = choice.next
        _save()

    return 0

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--play", action="store_true", help="Interactive play mode")
    parser.add_argument("--max-rounds", type=int, default=20, help="Max rounds for --play")
    parser.add_argument("--pc-wizard", action="store_true", help="Create a party JSON via prompts")
    parser.add_argument("--out", type=str, help="Output path for --pc-wizard", default="pc.json")
    parser.add_argument("--preset", choices=["fighter", "rogue", "wizard"], help="Preset party for --pc-wizard", default=None)
    parser.add_argument("--force", action="store_true", help="Force reindexing of the vector store")
    parser.add_argument("--json-out", nargs="?", const="logs/last_sidecar.json", help="Write sidecar JSON to path", default=None)
    parser.add_argument("--md-out", type=str, help="Write markdown output to path", default=None)
    parser.add_argument("--scene", type=str, help="Start a seed encounter", default=None)
    parser.add_argument("--resume", type=str, help="Resume session from JSON file", default=None)
    parser.add_argument(
        "--start",
        nargs="?",
        const="__AUTO__",  # allows bare `--start`
        help="Start the campaign. Optionally pass a SCENE key; bare --start uses the YAML 'start'.",
    )
    parser.add_argument("--save", type=str, help="Save session state", default=None)
    parser.add_argument("--embeddings", choices=["auto", "bge-small", "none"], default="auto")
    parser.add_argument("--pc", type=str, help="Path to PC sheet JSON", default=None)
    parser.add_argument("--campaign", type=str, help="Path to campaign folder or YAML. If a folder, we'll look for campaign.yaml (or index.yaml).", default=None)
    parser.add_argument("--seed", type=int, default=None,
                        help="Deterministic seed for dice/combat/session")
    parser.add_argument("--encounter", type=str, help="Monsters to fight", default=None)
    parser.add_argument("--rounds", type=int, help="Max combat rounds", default=10)
    parser.add_argument("--summary-out", type=str, help="Write encounter summary JSON", default=None)
    parser.add_argument("--autosave", action="store_true", help="Autosave turn summaries")
    parser.add_argument("--packs", type=str, default="srd", help="Comma-separated content packs")
    args = parser.parse_args()



    def _resolve_campaign_path(arg: str) -> Path:
        """Accept a YAML file or a directory containing one."""
        p = Path(arg)
        if p.is_dir():
            for name in ("campaign.yaml", "campaign.yml", "index.yaml", "index.yml"):
                cand = p / name
                if cand.exists():
                    return cand
            for cand in sorted(p.glob("*.y*ml")):
                return cand
            raise FileNotFoundError(f"No campaign YAML found in directory: {p}")
        return p

    if args.pc_wizard:
        from grimbrain import pc_wizard

        pc_wizard.main(out=args.out, preset=args.preset)
        return

    if args.campaign:
        import yaml

        campaign_path = _resolve_campaign_path(args.campaign)
        with open(campaign_path, "r", encoding="utf-8") as f:
            campaign_yaml = yaml.safe_load(f)
        if args.resume:
            start_key = None
        else:
            if args.start is None or args.start == "__AUTO__":
                start_key = campaign_yaml.get("start")
            else:
                start_key = args.start
        pcs_override = load_party_file(Path(args.pc)) if args.pc else None
        ret = run_campaign_cli(
            campaign_path,
            start=start_key,
            resume=args.resume,
            save=args.save,
            seed=args.seed,
            pcs=pcs_override,
            interactive=args.play,
            max_rounds=args.max_rounds,
        )
        if ret:
            sys.exit(ret)
        return

    if args.play:
        if not args.pc:
            raise SystemExit("--pc required for --play")
        if not args.encounter:
            raise SystemExit("--encounter required for --play")
        pcs = load_party_file(Path(args.pc))

        pack_names = [p.strip() for p in (args.packs or "").split(",") if p.strip()]
        catalog = load_packs(pack_names)

        def _lookup(name: str) -> MonsterSidecar:
            data = catalog.get(name.lower())
            if data:
                return MonsterSidecar(**data)
            return _lookup_fallback(name)

        monsters = parse_monster_spec(args.encounter, _lookup)
        play_cli(
            pcs,
            monsters,
            seed=args.seed,
            max_rounds=args.max_rounds,
            autosave=args.autosave,
            summary_out=args.summary_out,
        )
        return

    if args.resume and not any([args.scene, args.pc, args.encounter, args.campaign, args.play]):
        session = Session.load(args.resume)
        print(f"Resumed scene '{session.scene}' with {len(session.steps)} steps")
        return

    from llama_index.core.settings import Settings
    from llama_index.core.llms.mock import MockLLM
    from grimbrain.retrieval.indexing import (
        wipe_chroma_store,
        load_and_index_grouped_by_folder,
        kill_other_python_processes,
    )
    from grimbrain.retrieval.query_router import run_query

    embed_model, msg = choose_embedding(args.embeddings)
    print(msg)
    log_entries.append({"file": "N/A", "entries": 0, "collection": "embed_model", "status": msg})

    Settings.llm = MockLLM()

    if args.force:
        kill_other_python_processes()
        wipe_chroma_store(log_entries)

    load_and_index_grouped_by_folder(Path("data"), embed_model, log_entries, force_wipe=args.force)

    with open(LOG_FILE, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=["file", "entries", "collection", "status"])
        writer.writeheader()
        writer.writerows(log_entries)
    print(f"\nLog saved to: {LOG_FILE}")

    md, js, _ = run_query("goblin boss", type="monster", embed_model=embed_model)
    print(md)
    write_outputs(md, js, args.json_out, args.md_out)

    md_path = json_path = None

    if args.scene and args.resume:
        parser.error("--scene and --resume are mutually exclusive")

    if args.scene:
        md_path, json_path = start_scene(args.scene, seed=args.seed)
        print(f"Started scene '{args.scene}', logs at {json_path}")
    if args.resume:
        session = Session.load(args.resume)
        md_path = Path(args.resume.replace('.json', '.md'))
        json_path = Path(args.resume)
        print(f"Resumed scene '{session.scene}' with {len(session.steps)} steps")
        # optionally run a round, etc.
        # result = run_round(session.party, session.monsters, seed=args.seed)

    if args.pc and args.encounter:
        raw = json.loads(Path(args.pc).read_text())
        # Accept either a list of PCs or {"party": [...]}
        if isinstance(raw, dict) and "party" in raw:
            raw = raw["party"]
        if not isinstance(raw, list):
            raise ValueError("PC file must be a list of PC objects or a dict with 'party' list.")
        # Normalize common alternate keys inside attacks
        def _normalize_pc(obj):
            attacks = obj.get("attacks", [])
            for atk in attacks:
                if "damage_dice" not in atk and "damage" in atk:
                    atk["damage_dice"] = atk.pop("damage")
                if "to_hit" not in atk and "attack_bonus" in atk:
                    atk["to_hit"] = atk["attack_bonus"]
            return obj
        raw = [_normalize_pc(o) for o in raw]
        pcs = [PC(**obj) for obj in raw]

        pack_names = [p.strip() for p in (args.packs or "").split(",") if p.strip()]
        catalog = load_packs(pack_names)

        def _lookup(name: str) -> MonsterSidecar:
            data = catalog.get(name.lower())
            if data:
                return MonsterSidecar(**data)
            _, sc, _ = run_query(name, type="monster", embed_model=embed_model)
            return MonsterSidecar(**sc)

        monsters = parse_monster_spec(args.encounter, _lookup)
        result = run_encounter(pcs, monsters, seed=args.seed, max_rounds=args.rounds)
        print("\n".join(result["log"]))
        if args.summary_out:
            path = Path(args.summary_out)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(result["summary"], indent=2))
            print(f"Summary written to {path}")
        if md_path and json_path:
            log_step(md_path, json_path, f"Encounter vs {args.encounter}", "\n".join(result["log"]))


if __name__ == "__main__":
    main()
