from pathlib import Path
import json
import textwrap

import pytest

from grimbrain.validation import load_pc, load_campaign, PrettyError


def test_load_pc_ok(tmp_path: Path) -> None:
    pc = {
        "name": "Elora",
        "class": "Wizard",
        "level": 1,
        "abilities": {"str": 8, "dex": 14, "con": 12, "int": 16, "wis": 10, "cha": 12},
        "ac": 12,
        "max_hp": 8,
    }
    p = tmp_path / "pc.json"
    p.write_text(json.dumps(pc), encoding="utf-8")
    obj = load_pc(p)
    assert obj.name == "Elora" and obj.level == 1


def test_load_pc_schema_error(tmp_path: Path) -> None:
    bad = {"name": "NoAbilities", "class": "Wizard", "level": 1, "ac": 12, "max_hp": 8}
    p = tmp_path / "pc.json"
    p.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(PrettyError):
        load_pc(p)


def test_load_campaign_ok(tmp_path: Path) -> None:
    yml = textwrap.dedent(
        """
        name: Starter
        party: [pc_wizard.json]
        packs: [srd]
        quests:
          - id: q1
            title: Prologue
            steps: [wake up, find staff]
        """
    )
    p = tmp_path / "campaign.yaml"
    p.write_text(yml, encoding="utf-8")
    obj = load_campaign(p)
    assert obj.name == "Starter" and obj.party[0] == "pc_wizard.json"


def test_load_campaign_schema_error(tmp_path: Path) -> None:
    yml = "name: MissingParty"  # party required
    p = tmp_path / "campaign.yaml"
    p.write_text(yml, encoding="utf-8")
    with pytest.raises(PrettyError):
        load_campaign(p)

