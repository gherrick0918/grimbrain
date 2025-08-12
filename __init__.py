# grimbrain/__init__.py
__all__ = [
    "__version__",
    "run_query",
]

__version__ = "0.1.0"

# handy re-exports (optional)
try:
    from .retrieval.query_router import run_query  # noqa: F401
except Exception:
    pass
