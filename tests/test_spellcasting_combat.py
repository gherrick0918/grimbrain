from grimbrain.engine.combat import run_encounter
from tests.test_combat_round import make_goblin
from grimbrain.models import SpellSidecar, Attack, PC

fireball = SpellSidecar(
    name="Fireball",
    level=3,
    school="Evocation",
    casting_time="1 action",
    range="150 feet",
    components="V,S,M",
    duration="Instantaneous",
    classes=["Wizard"],
    text="A bright streak flares.",
    provenance=["PHB"],
)

caster = PC(
    name="Mage",
    ac=12,
    hp=20,
    attacks=[
        Attack(
            name="Fireball",
            damage_dice="8d6",
            type="spell",
            save_dc=13,
            save_ability="dex",
            spell=fireball,
        )
    ],
    spell_slots={3: 1},
)


def test_fireball_saves_and_damage():
    goblins = [make_goblin(), make_goblin(), make_goblin()]
    res = run_encounter([caster], goblins, seed=1, max_rounds=1)
    mons = res["state"]["monsters"]
    losses = [7 - m["hp"] for m in mons]
    assert losses == [28, 28, 14]


def test_spell_slot_depletion():
    tough = make_goblin()
    tough.hp = "100"
    res = run_encounter([caster], [tough], seed=1, max_rounds=2)
    mons = res["state"]["monsters"]
    # Only one casting due to a single slot
    assert 0 < mons[0]["hp"] < 100


def test_concentration_breaks_on_damage():
    bolt = SpellSidecar(
        name="Bolt",
        level=1,
        school="Evocation",
        casting_time="1 action",
        range="120 feet",
        components="V,S",
        duration="Concentration",
        classes=["Wizard"],
        text="Bolt",
        provenance=["PHB"],
    )
    conc_caster = PC(
        name="Mage",
        ac=12,
        hp=20,
        attacks=[
            Attack(
                name="Bolt",
                damage_dice="1d6",
                type="spell",
                to_hit=5,
                spell=bolt,
                concentration=True,
                level=1,
            )
        ],
        spell_slots={1: 1},
        con_mod=0,
    )
    goblin = make_goblin()
    res = run_encounter([conc_caster], [goblin], seed=9, max_rounds=1)
    assert any("loses concentration" in l for l in res["log"])
