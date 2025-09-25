from pathlib import Path
import random

from grimbrain.engine.characters import build_partymember
from grimbrain.engine.util import make_combatant_from_party_member
from grimbrain.engine.combat import resolve_attack
from grimbrain.engine.types import Target
from grimbrain.engine.damage import apply_defenses
from grimbrain.engine.saves import roll_save
from grimbrain.codex.weapons import WeaponIndex


class FixedRandom(random.Random):
    def __init__(self, sequence):
        super().__init__()
        self._sequence = list(sequence)

    def randint(self, a, b):  # noqa: D401 - deterministic sequence helper
        return self._sequence.pop(0)


def _make_combatant(pm, *, team="A"):
    cmb = make_combatant_from_party_member(pm, team=team, cid=pm.id)
    return cmb


def test_darkness_disadvantage_without_darkvision():
    idx = WeaponIndex.load(Path("data/weapons.json"))
    attacker = build_partymember(
        name="Attacker",
        cls="Fighter",
        scores={"STR": 16, "DEX": 10, "CON": 14, "INT": 10, "WIS": 10, "CHA": 8},
        weapon="Longsword",
        ranged=False,
    )
    defender = build_partymember(
        name="Defender",
        cls="Fighter",
        scores={"STR": 12, "DEX": 10, "CON": 12, "INT": 10, "WIS": 10, "CHA": 10},
        weapon="Spear",
        ranged=False,
    )
    atk_cmb = _make_combatant(attacker)
    def_cmb = _make_combatant(defender)
    atk_cmb.environment_light = "dark"
    def_cmb.environment_light = "dark"
    res = resolve_attack(
        atk_cmb.actor,
        attacker.weapon_primary,
        Target(ac=def_cmb.ac, hp=def_cmb.hp),
        idx,
        base_mode="none",
        rng=random.Random(1),
        forced_d20=(12, 7),
        attacker_state=atk_cmb,
        defender_state=def_cmb,
    )
    assert res["mode"] == "disadvantage"
    assert any("darkness" in note for note in res.get("notes", []))


def test_darkvision_negates_darkness_penalty():
    idx = WeaponIndex.load(Path("data/weapons.json"))
    attacker = build_partymember(
        name="Seer",
        cls="Fighter",
        scores={"STR": 16, "DEX": 10, "CON": 14, "INT": 10, "WIS": 10, "CHA": 8},
        weapon="Longsword",
        ranged=False,
        features={"darkvision": 60},
    )
    defender = build_partymember(
        name="Target",
        cls="Fighter",
        scores={"STR": 12, "DEX": 10, "CON": 12, "INT": 10, "WIS": 10, "CHA": 10},
        weapon="Spear",
        ranged=False,
    )
    atk_cmb = _make_combatant(attacker)
    def_cmb = _make_combatant(defender)
    atk_cmb.environment_light = "dark"
    res = resolve_attack(
        atk_cmb.actor,
        attacker.weapon_primary,
        Target(ac=def_cmb.ac, hp=def_cmb.hp),
        idx,
        base_mode="none",
        rng=random.Random(2),
        forced_d20=(12, 7),
        attacker_state=atk_cmb,
        defender_state=def_cmb,
    )
    assert res["mode"] == "none"


def test_poison_resistance_halves_damage():
    pm = build_partymember(
        name="Brokk",
        cls="Fighter",
        scores={"STR": 16, "DEX": 10, "CON": 14, "INT": 10, "WIS": 10, "CHA": 8},
        weapon="Warhammer",
        ranged=False,
        features={"resist": ["poison"]},
    )
    cmb = _make_combatant(pm)
    final, notes, _ = apply_defenses(10, "poison", cmb)
    assert final == 5
    assert any("resistant" in note for note in notes)


def test_advantage_on_poison_saves():
    pm = build_partymember(
        name="Stone",
        cls="Fighter",
        scores={"STR": 16, "DEX": 10, "CON": 14, "INT": 10, "WIS": 10, "CHA": 8},
        weapon="Warhammer",
        ranged=False,
        features={"adv_saves_tags": ["poison"]},
    )
    cmb = _make_combatant(pm)
    ok_plain, die_plain, (plain1, plain2) = roll_save(
        cmb.actor, "CON", 10, rng=FixedRandom([3, 15]), combatant=cmb
    )
    rng_adv = FixedRandom([3, 15])
    ok_adv, die_adv, (adv1, adv2) = roll_save(
        cmb.actor, "CON", 10, rng=rng_adv, combatant=cmb, tag="poison"
    )
    assert plain1 == 3 and die_plain == 3
    assert ok_plain is ((plain1 + cmb.con_mod) >= 10)
    assert adv1 == 3 and adv2 == 15 and die_adv == 15
    assert ok_adv is (15 + cmb.con_mod >= 10)
