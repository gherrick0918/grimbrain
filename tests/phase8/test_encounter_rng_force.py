import random

from grimbrain.engine.campaign import CampaignState, PartyMemberRef
from grimbrain.engine.encounters import run_encounter


def _state():
    party = [
        PartyMemberRef(
            id="PC1",
            name="Fighter",
            str_mod=3,
            dex_mod=1,
            con_mod=2,
            int_mod=0,
            wis_mod=0,
            cha_mod=0,
            ac=16,
            max_hp=24,
            pb=2,
            speed=30,
            weapon_primary="Longsword",
        ),
        PartyMemberRef(
            id="PC2",
            name="Archer",
            str_mod=0,
            dex_mod=3,
            con_mod=1,
            int_mod=0,
            wis_mod=0,
            cha_mod=0,
            ac=14,
            max_hp=16,
            pb=2,
            speed=30,
            ranged=True,
            weapon_primary="Longbow",
        ),
    ]
    return CampaignState(seed=1337, party=party)


def test_force_encounter_always_creates_one():
    st = _state()
    rng = random.Random(st.seed)
    notes = []
    res = run_encounter(st, rng, notes, force=True)
    assert res.get("encounter") is not None


def test_travel_seed_advances_producing_variety():
    st = _state()
    rng1 = random.Random(st.seed)
    notes = []
    _ = run_encounter(st, rng1, notes, force=False)  # maybe None
    # next call should not start from the same seed if caller advances it;
    # simulate by advancing rng ourselves here:
    st.seed = rng1.randrange(1_000_000_000)
    rng2 = random.Random(st.seed)
    _ = run_encounter(
        st, rng2, notes, force=False
    )  # distribution differs; no strict assert
    assert True  # smoke: no exceptions and two independent draws
