from grimbrain.retrieval.indexing import _build_global_lookup

def test_dedupe_prefers_longer():
    e1 = {"name": "Goblin", "source": "MM", "text": "short"}
    e2 = {"name": "Goblin", "source": "MM", "text": "a much longer description"}
    lookup = _build_global_lookup([e1, e2])
    assert len(lookup) == 1
    assert lookup[("Goblin", "MM")]["text"] == "a much longer description"
