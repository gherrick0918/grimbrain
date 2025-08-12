__all__ = ["__version__", "run_query"]
__version__ = "0.1.0"

# handy re-export for convenience
try:
    from .retrieval.query_router import run_query  # noqa: F401
except Exception:
    pass
