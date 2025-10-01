import json

import pytest

try:  # Typer >=0.9
    from typer.testing import CliRunner  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - compatibility for older Typer
    from click.testing import CliRunner  # type: ignore

from grimbrain.models.campaign import CampaignState
from grimbrain.scripts import campaign_play as cp


runner = CliRunner()


def _require_real_typer() -> None:
    if not hasattr(cp.app, "main"):
        pytest.skip("Typer runner not available")


def test_sample_json_then_status(tmp_path):
    _require_real_typer()
    demo = tmp_path / "demo.json"
    result = runner.invoke(cp.app, ["sample", str(demo), "-f"])
    assert result.exit_code == 0
    assert demo.exists()
    data = json.loads(demo.read_text(encoding="utf-8"))
    assert data["day"] == 1
    status = runner.invoke(cp.app, ["status", "--load", str(demo)])
    assert status.exit_code == 0
    output_text = status.stdout or status.output
    assert "day" in output_text.lower() or "location" in output_text.lower()
    state = cp.load_campaign(demo)
    assert isinstance(state, CampaignState)
    assert state.day >= 1
