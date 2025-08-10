import json
import hashlib
import os
import psutil
import shutil
import stat
from collections import defaultdict
from pathlib import Path
from chromadb import PersistentClient
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.node_parser import SimpleNodeParser
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.schema import Document
from utils import infer_root_key, resolve_copy, stamp_doc_meta, ensure_collection

HASH_CACHE_FILE = "hash_cache.json"

def calculate_sha256(file_path: Path) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()

def load_hash_cache() -> dict:
    if Path(HASH_CACHE_FILE).exists():
        with open(HASH_CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_hash_cache(cache: dict):
    with open(HASH_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)

def kill_other_python_processes():
    current_pid = os.getpid()
    current_cmdline = " ".join(psutil.Process(current_pid).cmdline())

    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if proc.info["name"] == "python.exe" and proc.pid != current_pid:
                other_cmdline = " ".join(proc.info["cmdline"])
                if "main.py" not in other_cmdline:
                    print(f"⚠️ Killing stray Python: PID={proc.pid}, CMD={other_cmdline}")
                    proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

def force_remove_readonly(func, path, _):
    os.chmod(path, stat.S_IWRITE)
    func(path)

def wipe_chroma_store(log_entries):
    store_path = Path("chroma_store")
    if store_path.exists():
        shutil.rmtree(store_path, onerror=force_remove_readonly)
        print(f"🗑️ Wiped Chroma store: {store_path}")
        log_entries.append({
            "file": "ALL",
            "entries": 0,
            "collection": "ALL",
            "status": "Wiped Chroma store"
        })
def flatten_field(value):
    if isinstance(value, dict):
        return ', '.join(f"{k}: {v}" for k, v in value.items())
    return str(value)

def load_and_index_grouped_by_folder(data_dir: Path, embed_model, log_entries, vector_dir="chroma_store", force_wipe=False):
    hash_cache = load_hash_cache()
    updated_hash_cache = hash_cache.copy()

    folder_to_changed_files, folder_entries, folder_filehash = _scan_json_files(
        data_dir, hash_cache, updated_hash_cache, log_entries, force_wipe
    )

    for folder, triples in folder_entries.items():
        safe_folder = "".join(c for c in folder if c.isalnum() or c in "_-").lower()
        collection_name = f"grim_{safe_folder}"

        all_entries = [e for _, e, _ in triples]
        global_lookup = _build_global_lookup(all_entries)

        docs = []
        for rel_path, raw_entry, changed in triples:
            resolved = resolve_copy(raw_entry, global_lookup) if raw_entry.get("_copy") else raw_entry
            stamped = stamp_doc_meta(resolved, collection_name)
            if changed:
                docs.append(_entry_to_doc(stamped))

        if not docs:
            continue

        _index_docs_to_chroma(
            docs, folder, folder_to_changed_files, collection_name, vector_dir, embed_model, log_entries
        )

    save_hash_cache(updated_hash_cache)

def _scan_json_files(data_dir, hash_cache, updated_hash_cache, log_entries, force_wipe):
    folder_to_changed_files = defaultdict(list)
    folder_entries = defaultdict(list)
    folder_filehash = {}

    for json_file in data_dir.rglob("*.json"):
        if json_file.name.startswith("fluff-") or "foundry" in json_file.name:
            continue

        rel_path = json_file.relative_to(data_dir)
        top_folder = rel_path.parts[0] if len(rel_path.parts) > 1 else rel_path.stem
        file_hash = calculate_sha256(json_file)
        folder_filehash[str(rel_path)] = file_hash

        changed = force_wipe or (str(rel_path) not in hash_cache or hash_cache[str(rel_path)] != file_hash)

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception as e:
            print(f"❌ Failed to load {rel_path}: {e}")
            log_entries.append({
                "file": str(rel_path), "entries": 0, "collection": "N/A", "status": f"Error: {e}"
            })
            continue

        # Support files that are:
        # - a dict with a root key (e.g., "monster", "spell", "data") holding a list
        # - a top-level list of entries
        # - a single dict entry
        if isinstance(raw, list):
            key = None
            entries = raw
        elif isinstance(raw, dict):
            key = infer_root_key(raw)
            if key and isinstance(raw.get(key), list):
                entries = raw.get(key, [])
            else:
                # Treat the dict itself as a single entry
                entries = [raw]
        else:
            key = None
            entries = []

        if not isinstance(entries, list):
            print(f"⚠️ Skipping {rel_path} (no list entries found)")
            continue

        for e in entries:
            folder_entries[top_folder].append((str(rel_path), e, changed))

        if changed:
            folder_to_changed_files[top_folder].append(str(rel_path))
            updated_hash_cache[str(rel_path)] = file_hash

    return folder_to_changed_files, folder_entries, folder_filehash

def _build_global_lookup(all_entries):
    return {
        (e.get("name"), e.get("source")): e
        for e in all_entries
        if e.get("name") and e.get("source")
    }

def _entry_to_doc(entry):
    name_value = entry.get("name", "Unknown")
    entry_type_raw = entry.get("type", "")
    entry_type = entry_type_raw.lower() if isinstance(entry_type_raw, str) else ""
    is_monster = "hp" in entry or "hit_points" in entry or entry_type in ["npc", "monster"]

    ac_val = entry.get("ac", entry.get("armor_class", "Unknown"))
    if isinstance(ac_val, list):
        ac_str = ", ".join(str(x.get("ac", x)) if isinstance(x, dict) else str(x) for x in ac_val)
    else:
        ac_str = str(ac_val)

    hp_val = entry.get("hp", entry.get("hit_points", "Unknown"))
    hp_str = str(hp_val.get("average", hp_val)) if isinstance(hp_val, dict) else str(hp_val)

    raw_speed = entry.get("speed", "Unknown")
    speed_str = ", ".join(f"{k}: {v}" for k, v in raw_speed.items()) if isinstance(raw_speed, dict) else str(raw_speed)
    raw_range = entry.get("range", "Unknown")
    range_str = ", ".join(str(v) for v in raw_range) if isinstance(raw_range, list) else str(raw_range)
    raw_damage = entry.get("damage", "Unknown")
    damage_str = ", ".join(str(v) for v in raw_damage) if isinstance(raw_damage, list) else str(raw_damage)
    raw_components = entry.get("components", [])
    components_str = ", ".join(raw_components) if isinstance(raw_components, list) else str(raw_components)
    duration_str = str(entry.get("duration", "Unknown"))
    casting_time_str = str(entry.get("time", "Unknown"))

    if is_monster:
        name = entry.get("name", "Unknown")
        description = entry.get("description", "")
        text = (
            f"{name}\n"
            f"{description}\n\n"
            f"AC: {ac_str}\n"
            f"HP: {hp_str}\n"
            f"Speed: {speed_str}\n"
            f"STR: {str(entry.get('str', 'Unknown'))}, "
            f"DEX: {str(entry.get('dex', 'Unknown'))}, "
            f"CON: {str(entry.get('con', 'Unknown'))}, "
            f"INT: {str(entry.get('int', 'Unknown'))}, "
            f"WIS: {str(entry.get('wis', 'Unknown'))}, "
            f"CHA: {str(entry.get('cha', 'Unknown'))}\n"
        )
        print(f"🧾 Indexed '{name_value}' as monster")

    elif "level" in entry or "school" in entry:
        body = entry.get("entries", entry.get("desc", []))
        level = entry.get("level", "Unknown")
        school = entry.get("school", "Unknown")
        text_body = "\n".join(str(line) for line in body) if isinstance(body, list) else str(body)
        text = (
            f"{name_value}\n"
            f"Level {level} {school}\n"
            f"Range: {range_str}\n"
            f"Damage: {damage_str}\n"
            f"Components: {components_str}\n"
            f"Duration: {duration_str}\n"
            f"Casting Time: {casting_time_str}\n\n"
            f"{text_body}"
        )
        print(f"📘 Indexed '{name_value}' as spell-like")
    else:
        lines = [f"{k}: {v}" for k, v in entry.items()]
        text = f"{name_value}\n" + "\n".join(lines)
        print(f"📦 Indexed '{name_value}' as generic")

    entry_metadata = {
        "source": str(entry.get("source", "Unknown")),
        "name": str(name_value)
    }

    if is_monster:
        entry_metadata.update({
            "type": "monster",
            "hp": hp_str,
            "ac": ac_str,
            "speed": speed_str
        })
    elif "level" in entry or "school" in entry:
        entry_metadata.update({
            "type": "spell",
            "level": str(entry.get("level", "Unknown")),
            "school": entry.get("school", "Unknown"),
            "range": range_str,
            "damage": damage_str,
            "components": components_str,
            "duration": duration_str,
            "casting_time": casting_time_str
        })
    else:
        entry_metadata["type"] = "generic"

    if entry.get("doc_type"):      entry_metadata["doc_type"]   = entry["doc_type"]
    if entry.get("is_variant") is not None: entry_metadata["is_variant"] = entry["is_variant"]
    if entry.get("variant_of"):    entry_metadata["variant_of"] = entry["variant_of"]
    if entry.get("priority") is not None:   entry_metadata["priority"]   = entry["priority"]
    if entry.get("canonical_id"):  entry_metadata["canonical_id"] = entry["canonical_id"]

    doc = Document(text=text, metadata=entry_metadata)
    return doc

def _index_docs_to_chroma(
    docs, folder, folder_to_changed_files, collection_name, vector_dir, embed_model, log_entries
):
    print(f"\n📦 Indexing collection '{collection_name}' with {len(docs)} updated documents...")
    log_entries.append({
        "file": ",".join(sorted(set(folder_to_changed_files[folder]))),
        "entries": len(docs),
        "collection": collection_name,
        "status": "Re-indexed (changed)"
    })

    chroma_client = PersistentClient(path=vector_dir)
    collection = ensure_collection(chroma_client, collection_name, embed_model)
    vector_store = ChromaVectorStore.from_collection(collection)

    for doc in docs:
        doc.metadata = flatten_metadata(doc.metadata)

    nodes = SimpleNodeParser().get_nodes_from_documents(docs)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex(nodes, storage_context=storage_context, embed_model=embed_model)
    index.storage_context.persist()

def flatten_metadata(meta: dict) -> dict:
    flat_meta = {}
    for k, v in meta.items():
        if isinstance(v, (dict, list)):
            flat_meta[k] = json.dumps(v, ensure_ascii=False)
        elif isinstance(v, (str, int, float)) or v is None:
            flat_meta[k] = v
        else:
            flat_meta[k] = str(v)
    return flat_meta
