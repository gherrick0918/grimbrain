import pytest


def test_single_token_retry(monkeypatch):
    calls = []

    class Node:
        def __init__(self, name: str):
            self.metadata = {"name": name, "source": "MM"}
            self.text = name

        def get_text(self):
            return self.text

    class Hit:
        def __init__(self, name: str):
            self.node = Node(name)
            self.score = 0.0

    class DummyQE:
        def __init__(self, top_k):
            self.top_k = top_k or 0

        def retrieve(self, q):
            if self.top_k < 100:
                return [Hit("goblin boss")]
            return [Hit("goblin"), Hit("goblin boss")]

    def fake_get_query_engine(collection, embed_model=None, top_k=None):
        calls.append(top_k)
        return DummyQE(top_k)

    import query_router

    monkeypatch.setattr(query_router, "get_query_engine", fake_get_query_engine)
    monkeypatch.setattr(query_router, "auto_format", lambda text, metadata=None: text)
    monkeypatch.setattr(query_router, "maybe_stitch_monster_actions", lambda *a, **k: None)
    monkeypatch.setattr(query_router, "_write_debug_log", lambda *a, **k: None)

    out = query_router.run_query("goblin", type="monster", embed_model=None, alias_map_enabled=False)
    assert "goblin" in out.lower()
    assert 50 in calls and 100 in calls

