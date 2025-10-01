import json
from pathlib import Path

import pytest

try:
    import yaml  # type: ignore[assignment]
except Exception:  # pragma: no cover - PyYAML is optional in tests too
    yaml = None  # type: ignore[assignment]

try:  # Typer <0.12 exposes the runner from click.testing instead
    from typer.testing import CliRunner  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - compatibility for older Typer
    from click.testing import CliRunner

from grimbrain.scripts import campaign_play as cp


runner = CliRunner()


def _require_real_typer() -> None:
    if not hasattr(cp.app, "main"):
        pytest.skip("Typer stub does not expose CLI runner")


def test_sample_defaults_then_status(tmp_path):
    _require_real_typer()
    demo = tmp_path / "demo.yaml"
    result = runner.invoke(cp.app, ["sample", str(demo), "--overwrite"])
    assert result.exit_code == 0
    assert demo.exists()
    out = result.stdout or result.output
    assert str(demo.resolve()) in out

    if cp.yaml is not None:
        status = runner.invoke(cp.app, ["status", "--load", str(demo)])
        assert status.exit_code == 0
        status_out = status.stdout or status.output
        assert "day" in status_out.lower() or "location" in status_out.lower()
    else:
        assert demo.read_text(encoding="utf-8").strip()


def test_sample_switches_and_parse(tmp_path):
    _require_real_typer()
    demo = tmp_path / "demo2.yaml"
    args = [
        "sample",
        str(demo),
        "-f",
        "--style",
        "heroic",
        "--day",
        "3",
        "--time",
        "evening",
        "--region",
        "Northreach",
        "--place",
        "Harbor",
        "--gold",
        "25",
        "--rations",
        "5",
        "--torches",
        "1",
        "--party",
        "Anya,Wizard,2,8,6",
        "--party",
        "Borin,Cleric,2",
        "--item",
        "potion=2",
        "--item",
        "rope=1",
    ]
    result = runner.invoke(cp.app, args)
    assert result.exit_code == 0
    out = result.stdout or result.output
    assert str(demo.resolve()) in out

    raw = Path(demo).read_text(encoding="utf-8")
    if cp.yaml is not None and yaml is not None:
        data = yaml.safe_load(raw)
    else:
        data = json.loads(raw)
    assert data["style"] == "heroic"
    assert data["clock"]["day"] == 3
    assert data["clock"]["time"] == "evening"
    assert data["location"] == "Northreach: Harbor"
    inv = data["inventory"]
    assert inv["rations"] == 5
    assert inv["torches"] == 1
    assert inv["potion"] == 2
    assert inv["rope"] == 1
    members = data["party"]
    assert members[0]["name"] == "Anya"
    assert members[0]["hp_current"] == 6
    assert members[1]["name"] == "Borin"
    assert members[1]["hp_max"] == 12
    assert data["party_info"]["gold"] == 25
    assert len(data["party_info"]["members"]) == 2


def test_sample_no_yaml(tmp_path, monkeypatch):
    _require_real_typer()
    import grimbrain.scripts.campaign_play as cp_module

    monkeypatch.setattr(cp_module, "yaml", None)
    demo = tmp_path / "demo.json"
    result = runner.invoke(
        cp_module.app,
        ["sample", str(demo), "-f", "--format", "json"],
    )
    assert result.exit_code == 0
    assert demo.exists()
    output = result.stdout or result.output
    assert str(demo.resolve()) in output
    assert demo.read_text(encoding="utf-8").strip().startswith("{")


def test_sample_stdout_json():
    _require_real_typer()
    result = runner.invoke(cp.app, ["sample", "--stdout", "--format", "json"])
    assert result.exit_code == 0
    output = result.stdout or result.output
    lines = [line for line in output.splitlines() if line.strip()]
    assert lines[0].startswith("{")
    assert lines[-1] == "(stdout)"
