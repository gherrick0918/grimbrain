import json
from collections import defaultdict
from pathlib import Path
from chromadb import PersistentClient
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.node_parser import SimpleNodeParser
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.schema import Document
from utils import infer_root_key

def wipe_chroma_store(log_entries, path="chroma_store"):
    client = PersistentClient(path=path)
    collections = client.list_collections()
    if not collections:
        print("📁 Chroma store is already empty.")
        log_entries.append({
            "file": "N/A", "entries": 0, "collection": "ALL", "status": "Chroma store already empty"
        })
        return
    for col in collections:
        print(f"🗑️ Deleting collection: {col.name}")
        client.delete_collection(col.name)
    log_entries.append({
        "file": "N/A", "entries": len(collections), "collection": "ALL", "status": "Chroma store wiped"
    })
    print("✅ All collections deleted.")

def load_and_index_grouped_by_folder(data_dir: Path, embed_model, log_entries, vector_dir="chroma_store"):
    folder_to_docs = defaultdict(list)

    for json_file in data_dir.rglob("*.json"):
        rel_path = json_file.relative_to(data_dir)
        top_folder = rel_path.parts[0] if len(rel_path.parts) > 1 else rel_path.stem

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception as e:
            print(f"❌ Failed to load {rel_path}: {e}")
            log_entries.append({
                "file": str(rel_path), "entries": 0, "collection": "N/A", "status": f"Error: {e}"
            })
            continue

        key = infer_root_key(raw)
        entries = raw.get(key, []) if key else []

        if not isinstance(entries, list):
            print(f"⚠️ Skipping {rel_path} (no list entries found)")
            continue

        for entry in entries:
            name_value = entry.get("name", "Unknown")
            body = entry.get("entries", entry.get("desc", []))
            text = "\n".join(str(line) for line in body) if isinstance(body, list) else str(body)
            folder_to_docs[top_folder].append(
                Document(text=f"{name_value}\n{text}", metadata={"source": name_value})
            )

        log_entries.append({
            "file": str(rel_path),
            "entries": len(entries),
            "collection": f"grim_{top_folder}",
            "status": "Success"
        })

    for folder, docs in folder_to_docs.items():
        collection_name = f"grim_{folder}"
        print(f"\n📦 Indexing collection '{collection_name}' with {len(docs)} documents...")
        chroma_client = PersistentClient(path=vector_dir)
        collection = chroma_client.get_or_create_collection(name=collection_name)
        vector_store = ChromaVectorStore.from_collection(collection)
        nodes = SimpleNodeParser().get_nodes_from_documents(docs)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        index = VectorStoreIndex(nodes, storage_context=storage_context, embed_model=embed_model)
        index.storage_context.persist()