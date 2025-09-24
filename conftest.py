"""Test helpers for environments without optional pytest plugins."""

import argparse
import importlib.util


def _addoption_if_missing(group, *args, **kwargs):
    try:
        group.addoption(*args, **kwargs)
    except argparse.ArgumentError:
        # pytest-cov (or another plugin) already registered this option.
        # Avoid raising during test discovery when coverage support is available.
        pass


def pytest_addoption(parser):
    if importlib.util.find_spec("pytest_cov") is not None:
        # pytest-cov is installed; it will register these options itself.
        return

    group = parser.getgroup("coverage", "coverage reporting")
    _addoption_if_missing(
        group,
        "--cov",
        action="append",
        default=[],
        help="(noop) accepted for compatibility when pytest-cov is unavailable.",
    )
    _addoption_if_missing(
        group,
        "--cov-report",
        action="append",
        default=[],
        help="(noop) accepted for compatibility when pytest-cov is unavailable.",
    )
    _addoption_if_missing(
        group,
        "--cov-fail-under",
        action="store",
        default=None,
        help="(noop) accepted for compatibility when pytest-cov is unavailable.",
    )
