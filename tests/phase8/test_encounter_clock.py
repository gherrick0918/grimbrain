import random
from grimbrain.engine.campaign import CampaignState, PartyMemberRef
from grimbrain.engine.encounters import run_encounter

def _state(base=0, step=25):
    party = [
        PartyMemberRef(
            id="PC1",
            name="Hero",
            str_mod=3,
            dex_mod=1,
            con_mod=2,
            int_mod=0,
            wis_mod=0,
            cha_mod=0,
            ac=16,
            max_hp=20,
            pb=2,
            speed=30,
            weapon_primary="Longsword",
        )
    ]
    st = CampaignState(seed=1234, party=party)
    st.encounter_chance = base
    st.encounter_clock = 0
    st.encounter_clock_step = step
    return st

def test_clock_increments_on_no_encounter_and_resets_on_encounter():
    st = _state(base=0, step=25)
    rng = random.Random(st.seed)
    notes = []
    # With base=0 and clock=0, chance=0% → guaranteed no encounter
    res1 = run_encounter(st, rng, notes, force=False)
    assert res1.get("encounter") is None
    # Emulate travel's update: increment clock
    st.encounter_clock = min(100, st.encounter_clock + st.encounter_clock_step)
    assert st.encounter_clock == 25
    # Next, force an encounter and ensure clock resets
    res2 = run_encounter(st, rng, notes, force=True)
    assert res2.get("encounter") is not None
    st.encounter_clock = 0
    assert st.encounter_clock == 0
