try:  # Typer <0.12 exposes the runner from click.testing instead
    from typer.testing import CliRunner  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - compatibility for older Typer
    from click.testing import CliRunner

from grimbrain.scripts import campaign_play as cp


runner = CliRunner()


def test_help_shows_and_mentions_known_command() -> None:
    # When running against the lightweight Typer stub bundled with the repo,
    # the app object does not expose Click's CLI machinery. In that scenario we
    # at least ensure the command table is populated with known commands.
    if not hasattr(cp.app, "main"):
        commands = getattr(cp.app, "commands", {})
        assert any(name in commands for name in {"travel", "run", "play"})
        return

    result = runner.invoke(cp.app, ["--help"], prog_name="campaign-play")
    assert result.exit_code == 0
    out = result.stdout or result.output
    assert "Usage:" in out
    assert "travel" in out or "run" in out or "play" in out
