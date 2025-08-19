import os


def instant_death_enabled() -> bool:
    """Return True if the instant death rule is enabled."""
    return os.getenv("GB_RULES_INSTANT_DEATH", "false").lower() == "true"
