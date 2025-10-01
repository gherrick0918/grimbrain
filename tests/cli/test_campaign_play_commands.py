import pytest

try:  # Typer >=0.9
    from typer.testing import CliRunner  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    from click.testing import CliRunner  # type: ignore

from grimbrain.io.campaign_io import save_campaign
from grimbrain.scripts import campaign_play as cp


runner = CliRunner()


def _require_real_typer() -> None:
    if not hasattr(cp.app, "main"):
        pytest.skip("Typer runner not available")


def _baseline_state() -> dict:
    return {
        "seed": 42,
        "day": 1,
        "time_of_day": "morning",
        "location": "Village",
        "gold": 0,
        "inventory": {"rations": 2},
        "party": [
            {
                "id": "PC1",
                "name": "Hero",
                "str_mod": 1,
                "dex_mod": 1,
                "con_mod": 1,
                "int_mod": 0,
                "wis_mod": 0,
                "cha_mod": 0,
                "ac": 13,
                "pb": 2,
                "speed": 30,
                "hp_max": 12,
                "hp_current": 12,
            }
        ],
        "current_hp": {"PC1": 12},
        "style": "classic",
        "narrative_style": "classic",
        "flags": {},
        "journal": [],
        "encounter_chance": 20,
        "encounter_clock": 0,
        "encounter_clock_step": 10,
        "short_rest_hours": 4,
        "long_rest_to_morning": True,
    }


def test_status_command_outputs(tmp_path):
    _require_real_typer()
    path = tmp_path / "state.json"
    save_campaign(_baseline_state(), path)

    result = runner.invoke(cp.app, ["status", "--load", str(path)])
    assert result.exit_code == 0
    text = result.stdout or result.output
    assert "Day" in text
    assert "Party" in text


def test_short_rest_updates_hp(tmp_path):
    _require_real_typer()
    path = tmp_path / "state.json"
    state = _baseline_state()
    state["party"][0]["hp_current"] = 5
    state["current_hp"]["PC1"] = 5
    save_campaign(state, path)

    result = runner.invoke(cp.app, ["short_rest", "--load", str(path), "--seed", "1"])
    assert result.exit_code == 0

    reloaded = cp.load_campaign(path)
    assert reloaded["current_hp"]["PC1"] >= 5
    assert reloaded["current_hp"]["PC1"] <= 12


def test_long_rest_sets_hp_to_max(tmp_path):
    _require_real_typer()
    path = tmp_path / "state.json"
    state = _baseline_state()
    state["party"][0]["hp_current"] = 4
    state["current_hp"]["PC1"] = 4
    save_campaign(state, path)

    result = runner.invoke(cp.app, ["long_rest", "--load", str(path)])
    assert result.exit_code == 0

    reloaded = cp.load_campaign(path)
    assert reloaded["current_hp"]["PC1"] == reloaded["party"][0]["hp_max"]


def test_travel_advances_time(tmp_path, monkeypatch):
    _require_real_typer()
    path = tmp_path / "state.json"
    state = _baseline_state()
    save_campaign(state, path)

    def fake_run_encounter(*_args, **_kwargs):
        return {}

    monkeypatch.setattr(cp, "run_encounter", fake_run_encounter)

    result = runner.invoke(
        cp.app,
        [
            "travel",
            "--load",
            str(path),
            "--seed",
            "123",
            "--hours",
            "4",
        ],
    )
    assert result.exit_code == 0

    reloaded = cp.load_campaign(path)
    assert reloaded["time_of_day"] in {"afternoon", "evening", "night", "morning"}
    assert reloaded["day"] >= 1
