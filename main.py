import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from llama_index.core.settings import Settings
from llama_index.llms.ollama import Ollama
from embedding import CustomSTEmbedding
from indexing import wipe_chroma_store, load_and_index_grouped_by_folder, kill_other_python_processes
from query import get_query_engine
from query_router import run_query
from llama_index.embeddings.ollama import OllamaEmbedding
from fallback_llm import MinimalFakeLLM
from llama_index.core.llms.mock import MockLLM

LOG_FILE = f"logs/index_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
log_entries = []

alwaysSmall = True

modelLlmMsg = ""
if alwaysSmall:
    embed_model = CustomSTEmbedding("sentence-transformers/all-MiniLM-L6-v2")
    modelLlmMsg = f"Using embedding model: {embed_model.model_name}"
else:
    try:
        embed_model = OllamaEmbedding("nomic-embed-text")
        modelLlmMsg = f"Using embedding model: {embed_model.model_name}"
    except Exception as e:
        embed_model = CustomSTEmbedding("sentence-transformers/all-MiniLM-L6-v2")
        modelLlmMsg = f"Falling back to embedding model: {embed_model.model_name} due to error: {e}"

print(modelLlmMsg)
log_entries.append({
    "file": "N/A",
    "entries": 0,
    "collection": "embed_model",
    "status": modelLlmMsg
})

if alwaysSmall:
    Settings.llm = MockLLM()
    modelllmMsg = "🟡 No real LLM assigned — using MockLLM for retrieval-only mode"
else:
    try:
        Settings.llm = Ollama(model="gemma:2b-instruct", base_url="http://localhost:11434")
        modelLlmMsg = "🧠 Using local LLM via Ollama (gemma:2b-instruct)"
    except Exception as e:
        modelLlmMsg = f"⚠️ Ollama not available, falling back to MockLLM: {e}"
        Settings.llm = MockLLM()

print(modelLlmMsg)
log_entries.append({
    "file": "N/A",
    "entries": 0,
    "collection": "LLM",
    "status": modelLlmMsg
})

parser = argparse.ArgumentParser()
parser.add_argument("--force", action="store_true", help="Force reindexing of the vector store")
parser.add_argument("--json-out", type=str, help="Path to write monster sidecar JSON", default=None)
args = parser.parse_args()

force = args.force

if force:
    kill_other_python_processes()
    wipe_chroma_store(log_entries)

load_and_index_grouped_by_folder(Path("data"), embed_model, log_entries, force_wipe=force)

with open(LOG_FILE, "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=["file", "entries", "collection", "status"])
    writer.writeheader()
    writer.writerows(log_entries)

print(f"\nLog saved to: {LOG_FILE}")

md, js, _ = run_query("goblin boss", type="monster", embed_model=embed_model)
print(md)
if args.json_out and js:
    out_path = Path(args.json_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(js, f, indent=2)
    print(f"Sidecar JSON written to {out_path}")
