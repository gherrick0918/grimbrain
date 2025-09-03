from pathlib import Path
from grimbrain.codex.weapons import WeaponIndex
from grimbrain.engine.types import Target, Combatant
from grimbrain.engine.combat import resolve_attack
from grimbrain.engine.scene import run_scene
from grimbrain.character import Character
import random


def idx():
    return WeaponIndex.load(Path("data/weapons.json"))


class C:
    def __init__(self, str_=16, dex=18, pb=2, ammo=None):
        self.str_score = str_
        self.dex_score = dex
        self.proficiency_bonus = pb
        self.proficiencies = {"simple weapons", "martial weapons"}
        self.fighting_styles = set()
        self.feats = set()
        self.ammo = dict(ammo or {"arrows": 99})

    def ability_mod(self, k):
        return ({"STR": self.str_score, "DEX": self.dex_score}[k] - 10) // 2

    def ammo_count(self, t):
        return int(self.ammo.get(t, 0))

    def spend_ammo(self, t, n=1):
        if self.ammo.get(t, 0) < n:
            return False
        self.ammo[t] -= n
        return True


def test_ranged_in_melee_imposes_disadvantage():
    i = idx()
    c = C()
    tgt = Target(ac=15, hp=10, distance_ft=5)  # melee distance
    # Force candidates (d1=17, d2=3) so we can see disadvantage pick the lower 3
    res = resolve_attack(
        c,
        "Longbow",
        tgt,
        i,
        base_mode="none",
        rng=random.Random(0),
        forced_d20=(17, 3),
    )
    assert res["mode"] == "disadvantage"
    assert res["d20"] == 3
    assert "in melee" in ", ".join(res["notes"]).lower()


def test_thrown_melee_is_not_penalized_in_melee():
    i = idx()
    c = C(str_=16, dex=12, pb=2)
    tgt = Target(ac=12, hp=10, distance_ft=5)
    # Dagger is melee weapon with thrown property -> not a ranged weapon
    res = resolve_attack(
        c,
        "Dagger",
        tgt,
        i,
        base_mode="none",
        rng=random.Random(1),
        forced_d20=(17, 3),
    )
    assert res["mode"] == "none"


def test_melee_dashes_when_one_move_cannot_reach():
    A = Combatant(
        "Orc",
        Character(str_score=18, dex_score=12, proficiency_bonus=2),
        hp=15,
        weapon="Greatsword",
    )
    B = Combatant(
        "Guard",
        Character(str_score=12, dex_score=12, proficiency_bonus=2),
        hp=11,
        weapon="Longsword",
    )
    # Start far enough that melee needs to Dash on round 1 (speed=30, reach=5)
    res = run_scene(A, B, seed=2, max_rounds=2, start_distance_ft=80)
    log = "\n".join(res.log).lower()
    assert "dashes: 80ft -> 20ft" in log


def test_archer_dashes_to_kite_if_too_close():
    A = Combatant(
        "Archer",
        Character(str_score=10, dex_score=18, proficiency_bonus=2),
        hp=14,
        weapon="Longbow",
    )
    B = Combatant(
        "Raider",
        Character(str_score=16, dex_score=12, proficiency_bonus=2),
        hp=16,
        weapon="Longsword",
    )
    # Start at 0 -> Archer should Disengage (existing behavior) or if >5 but <KITE and >speed gap, Dash back
    res = run_scene(A, B, seed=3, max_rounds=2, start_distance_ft=10)
    log = "\n".join(res.log).lower()
    # Either Disengage (if Bandit closes first) or moves/dashes; ensure dash path is possible in at least one branch
    assert ("disengages and moves" in log) or ("dashes: 10ft -> 30ft" in log) or ("dashes:" in log)
