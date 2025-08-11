import json
import os
from pathlib import Path
from grimbrain.retrieval.query_router import run_query


def test_goblin_golden(embedder):
    md, js, _ = run_query(type="monster", query="goblin", embed_model=embedder)
    base = Path(__file__).parent / "golden" / "goblin"
    md_path = base.with_suffix(".md")
    json_path = base.with_suffix(".json")
    if os.getenv("UPDATE_GOLDENS"):
        md_path.write_text(md)
        json_path.write_text(json.dumps(js, indent=2))
    assert md_path.read_text() == md
    assert json.loads(json_path.read_text()) == js
