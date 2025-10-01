from grimbrain.models.campaign import CampaignState


def test_campaignstate_roundtrip_basic():
    st = CampaignState(
        seed=42,
        day=2,
        time_of_day="afternoon",
        location="Wilderness",
        gold=7,
        inventory={"rations": 3},
        party=[{"id": "Aria", "name": "Aria", "hp_max": 11, "hp_current": 11}],
        style="classic",
        flags={"mode": "solo"},
        journal=["entry"],
    )
    data = st.to_dict()
    st2 = CampaignState.from_dict(data)
    assert st2.day == 2
    assert st2.time_of_day == "afternoon"
    assert st2.party[0]["name"] == "Aria"
    assert st2.party[0]["hp_current"] == 11
    assert st2.flags["mode"] == "solo"
    assert st2.journal == ["entry"]


def test_from_dict_legacy_shapes():
    legacy = {
        "seed": 5,
        "clock": {"day": 1, "time": "evening"},
        "location": {"region": "Greenfields", "place": "Village Gate"},
        "party": {
            "gold": 12,
            "members": [
                {
                    "id": "PC1",
                    "name": "Scout",
                    "hp": {"max": 12, "current": 8},
                    "ac": 13,
                    "pb": 2,
                }
            ],
        },
        "inventory": {"rations": 2},
        "state": {"current_hp": {"PC1": 8}},
    }
    st = CampaignState.from_dict(legacy)
    assert st.day == 1 and st.time_of_day == "evening"
    assert st.location == "Village Gate"
    assert st.gold == 12
    assert st.party[0]["name"] == "Scout"
    assert st.party[0]["hp_current"] == 8
