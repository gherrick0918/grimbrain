import random
from pathlib import Path

from grimbrain.engine.types import Combatant, Target
from grimbrain.engine.combat import (
    take_dodge_action,
    take_help_action,
    take_ready_action,
    resolve_attack,
)
from grimbrain.engine.round import start_turn
from grimbrain.character import Character
from grimbrain.codex.weapons import WeaponIndex


def C(str_=16, dex=16):
    return Character(
        str_score=str_,
        dex_score=dex,
        con_score=14,
        int_score=10,
        wis_score=10,
        cha_score=10,
        proficiency_bonus=2,
        proficiencies={"simple weapons", "martial weapons"},
    )


def test_dodge_imposes_disadvantage_on_attack_against_defender():
    idx = WeaponIndex.load(Path("data/weapons.json"))
    rng = random.Random(40)
    defender = Combatant("Dodger", C(), hp=12, weapon="Longsword")
    attacker = Combatant("Attacker", C(), hp=12, weapon="Longsword")
    take_dodge_action(defender)
    res = resolve_attack(
        attacker.actor,
        attacker.weapon,
        Target(ac=15, hp=defender.hp, distance_ft=5),
        idx,
        rng=rng,
        forced_d20=(17, 3),
        attacker_state=attacker,
        defender_state=defender,
    )
    assert res["mode"] == "disadvantage" and any(
        "defender dodging" in n for n in res["notes"]
    )


def test_help_grants_adv_once_then_consumes_token():
    idx = WeaponIndex.load(Path("data/weapons.json"))
    rng = random.Random(41)
    ally = Combatant("Ally", C(), hp=12, weapon="Longsword")
    helper = Combatant("Helper", C(), hp=10, weapon="Dagger")
    enemy = Combatant("Enemy", C(), hp=12, weapon="Longsword")
    take_help_action(helper, ally, enemy)
    res = resolve_attack(
        ally.actor,
        ally.weapon,
        Target(ac=13, hp=enemy.hp, distance_ft=5),
        idx,
        rng=rng,
        forced_d20=(3, 19),
        attacker_state=ally,
        defender_state=enemy,
    )
    assert res["mode"] == "advantage" and res["d20"] == 19
    assert ally.help_tokens.get(enemy.id, 0) == 0


def test_ready_structure_present_and_clears_on_start():
    actor = Combatant("Watcher", C(), hp=10, weapon="Longsword")
    foe = Combatant("Foe", C(), hp=10, weapon="Club")
    take_ready_action(actor, "enemy_within_30ft", foe.id)
    assert actor.readied_action is not None and actor.readied_action.target_id == foe.id
    actor.dodging = True
    actor.help_tokens["x"] = 1
    start_turn(None, actor, random.Random(1), [])
    assert not actor.dodging and not actor.help_tokens and actor.readied_action is None
