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
from engine.session import Session, start_scene

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

    if args.scene and args.resume:
        parser.error("--scene and --resume are mutually exclusive")

    if args.scene:
        md_path, json_path = start_scene(args.scene)
        print(f"Started scene '{args.scene}', logs at {json_path}")
    if args.resume:
        session = Session.load(args.resume)
        print(f"Resumed scene '{session.scene}' with {len(session.steps)} steps")


if __name__ == "__main__":
    main()
