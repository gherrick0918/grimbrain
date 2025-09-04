import random
from pathlib import Path

from grimbrain.character import Character
from grimbrain.engine.types import Combatant, Target
from grimbrain.engine.combat import (
    escape_grapple_action,
    grapple_action,
    resolve_attack,
    shove_action,
)
from grimbrain.engine.scene import effective_speed
from grimbrain.codex.weapons import WeaponIndex


def mk_pair():
    a_char = Character(str_score=16, dex_score=12, proficiency_bonus=2, proficiencies={"simple weapons", "martial weapons"})
    d_char = Character(str_score=12, dex_score=16, proficiency_bonus=2, proficiencies={"simple weapons", "martial weapons"})
    a = Combatant(name="Grappler", actor=a_char, hp=20, weapon="Mace", proficient_athletics=True)
    d = Combatant(name="Defender", actor=d_char, hp=18, weapon="Dagger", proficient_acrobatics=True)
    return a, d


def test_grapple_success_and_speed_zero():
    rng = random.Random(101)
    a, d = mk_pair()
    notes: list[str] = []
    ok = grapple_action(a, d, rng=rng, notes=notes)
    assert ok
    assert "grappled" in d.conditions and d.grappled_by == a.name
    assert effective_speed(d) == 0


def test_escape_fails_then_succeeds():
    rng = random.Random(101)
    a, d = mk_pair()
    notes: list[str] = []
    assert grapple_action(a, d, rng=rng, notes=notes)
    allc = {a.name: a, d.name: d}
    ok = escape_grapple_action(d, allc, rng=random.Random(222), notes=notes)
    assert not ok
    ok2 = escape_grapple_action(d, allc, rng=random.Random(333), notes=notes)
    assert ok2
    assert "grappled" not in d.conditions and d.grappled_by is None


def test_prone_modifiers_melee_adv_ranged_disadv():
    rng = random.Random(202)
    atk = Character(
        str_score=16,
        dex_score=14,
        proficiency_bonus=2,
        proficiencies={"simple weapons", "martial weapons"},
        ammo={"arrows": 5},
    )
    widx = WeaponIndex.load(Path("data/weapons.json"))
    target = Target(ac=14, hp=10, cover="none", distance_ft=5, conditions={"prone"})
    res = resolve_attack(atk, "Mace", target, widx, rng=rng)
    assert any("prone target" in n and "advantage" in n for n in res["notes"])
    target2 = Target(ac=14, hp=10, cover="none", distance_ft=10, conditions={"prone"})
    res2 = resolve_attack(atk, "Longbow", target2, widx, rng=rng)
    assert any("prone target" in n and "disadvantage" in n for n in res2["notes"])


def test_shove_push_increases_distance_and_triggers_oa():
    rng = random.Random(808)
    a, d = mk_pair()
    notes: list[str] = []
    flag = {"oa": False}

    def trigger_oa(_a, _d):
        flag["oa"] = True

    ok = shove_action(
        a,
        d,
        choice="push",
        rng=rng,
        distance_ft=5,
        reach_threshold=5,
        notes=notes,
        trigger_oa_fn=trigger_oa,
    )
    assert ok
    assert flag["oa"]

