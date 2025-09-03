import random
from .types import DeathState


def reset_death_state(ds: DeathState) -> None:
    ds.successes = ds.failures = 0
    ds.stable = False
    ds.dead = False


def roll_death_save(ds: DeathState, rng: random.Random) -> str:
    if ds.stable or ds.dead:
        return "no-op"
    d = rng.randint(1, 20)
    if d == 1:
        ds.failures += 2
        outcome = "crit-fail"
    elif d == 20:
        reset_death_state(ds)
        ds.stable = True  # immediately ends the sequence
        outcome = "crit-success-1hp"
    elif d >= 10:
        ds.successes += 1
        outcome = "success"
    else:
        ds.failures += 1
        outcome = "fail"

    if ds.successes >= 3:
        ds.stable = True
        outcome += "|stable"
    if ds.failures >= 3:
        ds.dead = True
        outcome += "|dead"
    return outcome


def apply_damage_while_down(ds: DeathState, *, melee_within_5ft: bool) -> None:
    if ds.stable or ds.dead:
        return
    ds.failures += 2 if melee_within_5ft else 1
    if ds.failures >= 3:
        ds.dead = True
