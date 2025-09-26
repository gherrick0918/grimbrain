from types import SimpleNamespace

from grimbrain.engine.campaign import (
    CampaignState,
    PartyMemberRef,
    load_campaign,
    save_campaign,
)
from grimbrain.scripts import campaign_play as cp


def _sample_party_member() -> PartyMemberRef:
    return PartyMemberRef(
        id="P1",
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
    )


def test_status_persists_global_style(tmp_path, capsys):
    path = tmp_path / "style_demo.json"
    state = CampaignState(seed=1, party=[_sample_party_member()])
    save_campaign(state, path.as_posix())
    ctx = SimpleNamespace(obj={"style": "heroic"}, parent=None)

    cp.status(ctx, load=path.as_posix())
    captured = capsys.readouterr()
    assert "Day" in captured.out

    updated = load_campaign(path.as_posix())
    assert updated.narrative_style == "heroic"
