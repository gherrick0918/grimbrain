def test_story_sample(monkeypatch, capsys):
    import sys
    import types

    sys.modules.setdefault(
        "grimbrain.retrieval.query_router", types.SimpleNamespace(run_query=lambda *a, **k: (None, None, None))
    )
    from grimbrain.scripts.campaign_play import story

    inputs = iter(["1"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    story("sample_campaign.yaml")
    out = capsys.readouterr().out
    assert "Ogre lies defeated" in out
    assert "You climbed the mountain" in out
