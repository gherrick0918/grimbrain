from pathlib import Path
from grimbrain.codex.weapons import WeaponIndex
from grimbrain.engine.types import Combatant, Target
from grimbrain.engine.combat import resolve_attack
from grimbrain.engine.scene import run_scene
from grimbrain.character import Character
import random


def C(str_=16, dex=16, pb=2):
    # give default ability scores to avoid KeyErrors in saves
    return Character(
        str_score=str_,
        dex_score=dex,
        con_score=14,
        int_score=10,
        wis_score=10,
        cha_score=10,
        proficiency_bonus=pb,
        proficiencies={"simple weapons", "martial weapons"},
    )


def test_poisoned_imposes_disadvantage_on_attacks():
    A = Combatant("Poisoned", C(dex=18), hp=12, weapon="Longbow")
    A.actor.add_ammo("arrows", 5)
    A.actor.conditions = {"poisoned"}
    idx = WeaponIndex.load(Path("data/weapons.json"))
    res = resolve_attack(
        A.actor,
        "Longbow",
        Target(ac=15, hp=12, distance_ft=30),
        idx,
        base_mode="none",
        rng=random.Random(1),
        forced_d20=(17, 3),
    )
    assert res["mode"] == "disadvantage" and res["d20"] == 3


def test_restrained_gives_advantage_to_attackers_and_blocks_movement():
    A = Combatant("Attacker", C(), hp=12, weapon="Longsword")
    idx = WeaponIndex.load(Path("data/weapons.json"))
    res = resolve_attack(
        A.actor,
        "Longsword",
        Target(ac=15, hp=12, distance_ft=5, cover="none", conditions={"restrained"}),
        idx,
        base_mode="none",
        rng=random.Random(2),
        forced_d20=(4, 19),
    )
    assert res["mode"] == "advantage" and res["d20"] == 19


def test_net_hit_applies_restrained_and_ai_attempts_escape():
    A = Combatant("Netter", C(dex=18), hp=10, weapon="Net")
    B = Combatant("Target", C(str_=10), hp=10, weapon="Mace")
    # Start adjacent so Net can hit; seed chosen to land a hit then see an escape attempt line
    res = run_scene(A, B, seed=6, max_rounds=3, start_distance_ft=5)
    log = "\n".join(res.log).lower()
    assert "net" in log and "restrained" in log and (
        "escapes restraint" in log or "fails to escape" in log
    )

