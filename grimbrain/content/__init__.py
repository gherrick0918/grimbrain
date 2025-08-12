# grimbrain/__init__.py
__all__ = ["__version__"]
__version__ = "0.1.0"

# Optional convenience re-export; ignore if not available at import time.
try:
    from grimbrain.retrieval.query_router import run_query  # noqa: F401
    __all__.append("run_query")
except Exception:
    pass
