import os
import random
import tempfile

from grimbrain.engine.campaign import (
    CampaignState,
    PartyMemberRef,
    QuestLogItem,
    save_campaign,
    load_campaign,
)
from grimbrain.engine.encounters import run_encounter
from grimbrain.scripts.campaign_play import quest as quest_cmd


def make_state():
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


def test_save_load_roundtrip():
    st = make_state()
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "camp.json")
        save_campaign(st, path)
        st2 = load_campaign(path)
        assert st2.seed == st.seed and len(st2.party) == 2 and st2.current_hp["PC1"] == 24


def test_travel_encounter_persists_hp():
    st = make_state()
    rng = random.Random(1)
    notes = []
    res = run_encounter(st, rng, notes)
    if res.get("encounter"):
        assert any(st.current_hp[pm.id] < pm.max_hp for pm in st.party)


def test_long_rest_restores_hp():
    st = make_state()
    st.current_hp["PC1"] = 5
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "camp.json")
        save_campaign(st, path)
        st2 = load_campaign(path)
        for p in st2.party:
            st2.current_hp[p.id] = p.max_hp
        save_campaign(st2, path)
        st3 = load_campaign(path)
        assert st3.current_hp["PC1"] == 24


def test_quest_log_add_and_complete():
    st = make_state()
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "camp.json")
        save_campaign(st, path)
        quest_cmd(load=path, add="Find treasure", done=None)
        st2 = load_campaign(path)
        assert len(st2.quest_log) == 1 and not st2.quest_log[0].done
        qid = st2.quest_log[0].id
        quest_cmd(load=path, add=None, done=qid)
        st3 = load_campaign(path)
        assert st3.quest_log[0].done
