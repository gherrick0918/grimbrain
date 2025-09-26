import os
import shutil
import tempfile

from grimbrain.engine.narrator import (
    ai_cached_generate_v2,
    _ai_cache_key_v2,
    _ai_cache_path_from_key,
)


def test_ai_cache_hit_and_write_visible():
    tmp = tempfile.mkdtemp()
    os.environ["GRIMBRAIN_AI_CACHE_DIR"] = tmp
    try:
        model, style, section = "gpt-test", "classic", "travel"
        tpl_id, location, time_bucket = "pack:sec:1", "Wilderness", "pm"

        gen1 = lambda: "FIRST"
        out1 = ai_cached_generate_v2(
            model,
            style,
            section,
            tpl_id,
            location,
            time_bucket,
            debug=True,
            generator=gen1,
        )
        assert out1 == "FIRST"

        gen2 = lambda: "SECOND"
        out2 = ai_cached_generate_v2(
            model,
            style,
            section,
            tpl_id,
            location,
            time_bucket,
            debug=True,
            generator=gen2,
        )
        assert out2 == "FIRST"

        key = _ai_cache_key_v2(model, style, section, tpl_id, location, time_bucket)
        assert _ai_cache_path_from_key(key).exists()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        os.environ.pop("GRIMBRAIN_AI_CACHE_DIR", None)
