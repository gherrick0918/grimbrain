import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from grimbrain.engine.campaign import CampaignState, PartyMemberRef
from grimbrain.engine.journal import log_event
from grimbrain.engine.campaign import save_campaign, load_campaign
from grimbrain.scripts import campaign_play


def test_log_event_persists_and_formats():
    st = CampaignState(
        seed=1,
        party=[
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
            )
        ],
    )
    assert st.journal == []
    log_event(st, "Travel 4h; No encounter", kind="travel", extra={"effective": 30})
    log_event(st, "Short rest", kind="rest", extra={"type": "short"})
    assert len(st.journal) == 2
    assert st.journal[0]["kind"] == "travel"
    assert "No encounter" in st.journal[0]["text"]
    assert st.journal[1]["extra"]["type"] == "short"


def test_cli_logging_and_journal_command(tmp_path, monkeypatch, capsys):
    st = CampaignState(
        seed=5,
        party=[
            PartyMemberRef(
                id="PC1",
                name="Scout",
                str_mod=1,
                dex_mod=2,
                con_mod=1,
                int_mod=0,
                wis_mod=0,
                cha_mod=0,
                ac=13,
                max_hp=12,
                pb=2,
                speed=30,
                weapon_primary="Bow",
            )
        ],
    )
    st.current_hp["PC1"] = 8
    path = tmp_path / "camp.json"
    save_campaign(st, str(path))

    results = iter(
        [
            {"encounter": "Bandits", "winner": "A", "rounds": 2},
            {"encounter": None},
        ]
    )

    def fake_run_encounter(state, rng, notes, force=False):
        return next(results, {"encounter": None})

    monkeypatch.setattr(campaign_play, "run_encounter", fake_run_encounter)
    campaign_play.travel(load=str(path), hours=4, seed=1, force_encounter=False, encounter_chance=None)
    campaign_play.travel(load=str(path), hours=4, seed=2, force_encounter=False, encounter_chance=None)
    campaign_play.short_rest(load=str(path), seed=3)
    campaign_play.long_rest(load=str(path))
    campaign_play.quest(load=str(path), add="Find the relic", done=None)
    campaign_play.quest(load=str(path), add=None, done="Q1")
    capsys.readouterr()

    loaded = load_campaign(str(path))
    kinds = [e["kind"] for e in loaded.journal]
    assert kinds.count("travel") == 2
    assert any("Encounter" in e["text"] for e in loaded.journal if e["kind"] == "travel")
    assert any("No encounter" in e["text"] for e in loaded.journal if e["kind"] == "travel")
    assert any(e["kind"] == "rest" for e in loaded.journal)
    assert any(e["kind"] == "quest" and "Find the relic" in e["text"] for e in loaded.journal)

    campaign_play.journal(load=str(path), tail=10, grep=None, clear=False)
    out = capsys.readouterr().out
    assert "(travel)" in out
    assert "Day" in out

    campaign_play.journal(load=str(path), tail=None, grep=None, clear=True)
    cleared_out = capsys.readouterr().out
    assert "Journal cleared" in cleared_out
    cleared_state = load_campaign(str(path))
    assert cleared_state.journal == []
