from grimbrain.config import flag


def instant_death_enabled() -> bool:
    """Return True if the instant death rule is enabled."""
    return flag("GB_RULES_INSTANT_DEATH", False)
