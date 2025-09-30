from pathlib import Path

import pytest
import yaml

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

    status = runner.invoke(cp.app, ["status", "--load", str(demo)])
    assert status.exit_code == 0
    out = status.stdout or status.output
    assert "day" in out.lower() or "location" in out.lower()


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

    data = yaml.safe_load(Path(demo).read_text(encoding="utf-8"))
    assert data["style"] == "heroic"
    assert data["clock"]["day"] == 3
    assert data["clock"]["time"] == "evening"
    assert data["location"]["region"] == "Northreach"
    assert data["location"]["place"] == "Harbor"
    assert data["party"]["gold"] == 25
    inv = data["inventory"]
    assert inv["rations"] == 5
    assert inv["torches"] == 1
    assert inv["potion"] == 2
    assert inv["rope"] == 1
    members = data["party"]["members"]
    assert members[0]["name"] == "Anya"
    assert members[0]["hp"]["current"] == 6
    assert members[1]["name"] == "Borin"
    assert members[1]["hp"]["max"] == 12
