import io
import contextlib

def test_suppress_embedding_warning(monkeypatch):
    monkeypatch.setenv("SUPPRESS_EMBED_WARNING", "1")
    from query_router import get_query_engine
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        get_query_engine("grim_bestiary", embed_model=None)
    assert "Embedding not configured" not in buf.getvalue()
