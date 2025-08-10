# tests/test_smoke.py
import os
from query_router import get_query_engine, rerank, _node_meta, run_query, _norm

def retrieve_with_backoff(collection, embedder, query, token, ks=(25, 50, 100, 200)):
    """Rebuild the QE with larger top_k until at least one NAME exactly matches the token."""
    goal = _norm(token)
    for k in ks:
        qe = get_query_engine(collection, embed_model=embedder, top_k=k)
        hits = qe.retrieve(query)
        names = [(_node_meta(h).get("name") or "") for h in hits]
        if any(goal == _norm(n) for n in names):
            return hits
    return hits  # last attempt

def test_monster_goblin_top(embedder):
    hits = retrieve_with_backoff("grim_bestiary", embedder, "goblin", "goblin")
    hits = rerank("goblin", hits)
    meta = _node_meta(hits[0])
    assert meta["name"].lower() == "goblin"


def test_rerank_exact_name_bubble():
    class Node:
        def __init__(self, name):
            self.metadata = {"name": name}
            self.text = name

    class Hit:
        def __init__(self, name, score):
            self.node = Node(name)
            self.score = score

    hits = [Hit("goblin boss", 0), Hit("goblin", -100)]
    results = rerank("goblin", hits)
    names = [(_node_meta(h).get("name") or "").lower() for h in results]
    assert names[0] == "goblin"
    assert names[1] == "goblin boss"

def test_monster_booyahg_whip(embedder):
    hits = retrieve_with_backoff("grim_bestiary", embedder, "booyahg whip", "booyahg")
    hits = rerank("booyahg whip", hits)
    meta = _node_meta(hits[0])
    assert meta["name"].lower().startswith("booyahg whip")
    assert meta.get("source") == "VGM"
    
def test_spell_fireball_format(embedder):
    out = run_query(type="spell", query="fireball", embed_model=embedder)
    assert "_3rd-level Evocation_" in out
    assert "**Damage:** 8d6" in out  # allow 8d6 fire or plain 8d6

def test_monster_booyahg_formatted_output(embedder):
    # Validate MonsterFormatter path via run_query without changing earlier test
    out = run_query(type="monster", query="booyahg whip", embed_model=embedder)
    low = out.lower()
    assert "armor class" in low
    assert "actions" in low

def test_spell_fireball_provenance(embedder):
    out = run_query(type="spell", query="fireball", embed_model=embedder)
    assert "sources considered" in out.lower()
