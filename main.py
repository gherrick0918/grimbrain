import argparse
import csv
import json
import os
from datetime import datetime
from pathlib import Path
from llama_index.core.settings import Settings
from llama_index.core.llms.mock import MockLLM
from indexing import wipe_chroma_store, load_and_index_grouped_by_folder, kill_other_python_processes
from query_router import run_query
from engine.session import Session, start_scene, log_step
from engine.combat import run_round, run_encounter, parse_monster_spec
from models import PC, MonsterSidecar

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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Force reindexing of the vector store")
    parser.add_argument("--json-out", nargs="?", const="logs/last_sidecar.json", help="Write sidecar JSON to path", default=None)
    parser.add_argument("--md-out", type=str, help="Write markdown output to path", default=None)
    parser.add_argument("--scene", type=str, help="Start a seed encounter", default=None)
    parser.add_argument("--resume", type=str, help="Resume session from JSON file", default=None)
    parser.add_argument("--embeddings", choices=["auto", "bge-small", "none"], default="auto")
    parser.add_argument("--pc", type=str, help="Path to PC sheet JSON", default=None)
    parser.add_argument("--seed", type=int, default=None,
                        help="Deterministic seed for dice/combat/session")
    parser.add_argument("--encounter", type=str, help="Monsters to fight", default=None)
    parser.add_argument("--rounds", type=int, help="Max combat rounds", default=10)
    parser.add_argument("--summary-out", type=str, help="Write encounter summary JSON", default=None)
    args = parser.parse_args()

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

        def _lookup(name: str) -> MonsterSidecar:
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
