import json
from pathlib import Path

from llama_index.core import Settings
from llama_index.core.llms.mock import MockLLM
from llama_index.core.embeddings.mock_embed_model import MockEmbedding

from grimbrain.retrieval.indexing import load_and_index_grouped_by_folder, wipe_chroma_store
from grimbrain.retrieval.query_router import get_query_engine, _node_meta


def test_monster_retrieval_from_chroma(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    goblin = {
        "monster": [
            {
                "name": "Goblin",
                "source": "MM",
                "ac": "15 (leather armor, shield)",
                "hp": "7 (2d6)",
                "speed": "30 ft.",
                "str": 8,
                "dex": 14,
                "con": 10,
                "int": 10,
                "wis": 8,
                "cha": 8,
                "traits": [],
                "actions": [],
            }
        ]
    }
    (data_dir / "bestiary.json").write_text(json.dumps(goblin))

    log = []
    wipe_chroma_store(log)
    embed = MockEmbedding(embed_dim=8)
    Settings.embed_model = embed
    Settings.llm = MockLLM()
    load_and_index_grouped_by_folder(data_dir, embed, log, force_wipe=True)

    qe = get_query_engine("grim_bestiary", embed_model=embed, top_k=1)
    results = qe.retrieve("goblin")
    assert results
    meta = _node_meta(results[0])
    assert meta.get("name") == "Goblin"
