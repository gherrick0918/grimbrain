"""Test helpers for environments without optional pytest plugins."""


def pytest_addoption(parser):
    group = parser.getgroup("coverage", "coverage reporting")
    group.addoption(
        "--cov",
        action="append",
        default=[],
        help="(noop) accepted for compatibility when pytest-cov is unavailable.",
    )
    group.addoption(
        "--cov-report",
        action="append",
        default=[],
        help="(noop) accepted for compatibility when pytest-cov is unavailable.",
    )
    group.addoption(
        "--cov-fail-under",
        action="store",
        default=None,
        help="(noop) accepted for compatibility when pytest-cov is unavailable.",
    )
