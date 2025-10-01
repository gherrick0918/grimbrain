from grimbrain.models.campaign import CampaignState


def test_campaign_state_roundtrip_simple():
    st = CampaignState(
        seed=123,
        day=3,
        time_of_day="dusk",
        location="Greenfields: Village Gate",
        gold=50,
        inventory={"rations": 5},
        party=[{"id": "PC1", "name": "Rin", "hp_max": 10, "hp_current": 8}],
        style="grim",
        flags={"blessed": True},
        journal=[{"day": 3, "note": "Arrived"}],
    )
    data = st.to_dict()
    st2 = CampaignState.from_dict(data)
    assert isinstance(st2, CampaignState)
    assert st2.day == st.day
    assert st2.time_of_day == st.time_of_day
    assert st2.party[0]["id"] == st.party[0]["id"]
    assert st2.party[0]["hp_current"] == 8
    assert st2.flags == {"blessed": True}
    assert st2.journal == [{"day": 3, "note": "Arrived"}]
