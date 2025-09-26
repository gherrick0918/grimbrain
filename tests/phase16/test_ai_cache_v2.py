import os
import shutil
import tempfile

from grimbrain.engine.narrator import ai_cached_generate_v2, _ai_index_load


def test_v2_hits_with_same_context():
    tmp = tempfile.mkdtemp()
    os.environ["GRIMBRAIN_AI_CACHE_DIR"] = tmp
    try:
        model, style, section = "openai:gpt-4o-mini", "grim", "travel"
        tpl_id, location, tb = "classic:travel_start:1", "Wilderness", "pm"
        calls = {"n": 0}

        def gen():
            calls["n"] += 1
            return f"OUT-{calls['n']}"

        out1 = ai_cached_generate_v2(
            model,
            style,
            section,
            tpl_id,
            location,
            tb,
            debug=False,
            generator=gen,
        )
        out2 = ai_cached_generate_v2(
            model,
            style,
            section,
            tpl_id,
            location,
            tb,
            debug=False,
            generator=gen,
        )
        assert out1 == out2 == "OUT-1"
        idx = _ai_index_load()
        assert len(idx) == 1
        hits = list(idx.values())[0]["hits"]
        assert hits >= 2
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        os.environ.pop("GRIMBRAIN_AI_CACHE_DIR", None)
