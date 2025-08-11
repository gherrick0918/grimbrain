from pathlib import Path
from main import write_outputs
from grimbrain.retrieval.query_router import run_query

def test_write_outputs(tmp_path, embedder):
    md, js, _ = run_query(type="monster", query="goblin", embed_model=embedder)
    jpath = tmp_path / "out.json"
    mpath = tmp_path / "out.md"
    write_outputs(md, js, jpath, mpath)
    assert jpath.exists()
    assert mpath.exists()
