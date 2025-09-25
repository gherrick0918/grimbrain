"""Lightweight shim of the llama_index package for Grimbrain tests.

This module implements just enough of the public surface used by the
project's retrieval pipeline so that we can run in environments where the
real llama_index dependency is unavailable or incompatible.  The goal is to
provide deterministic, dependency-free behaviour for unit tests while
mirroring the small subset of APIs we rely on.
"""

from . import core  # re-export for convenience
from . import vector_stores

__all__ = ["core", "vector_stores"]
