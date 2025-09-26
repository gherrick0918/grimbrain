import os
import shutil
import tempfile

from grimbrain.engine.narrator import ai_cached_generate, _ai_cache_path


def test_ai_cache_hit_and_write_visible():
    tmp = tempfile.mkdtemp()
    os.environ["GRIMBRAIN_AI_CACHE_DIR"] = tmp
    try:
        model, style, section, text = "gpt-test", "classic", "travel", "Hello world"

        gen1 = lambda prompt, model_name: "FIRST"
        out1 = ai_cached_generate(
            model,
            style,
            section,
            text,
            debug=True,
            generator=gen1,
        )
        assert out1 == "FIRST"

        gen2 = lambda prompt, model_name: "SECOND"
        out2 = ai_cached_generate(
            model,
            style,
            section,
            text,
            debug=True,
            generator=gen2,
        )
        assert out2 == "FIRST"

        assert _ai_cache_path(model, style, section, text).exists()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        os.environ.pop("GRIMBRAIN_AI_CACHE_DIR", None)
