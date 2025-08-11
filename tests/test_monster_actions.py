from grimbrain.formatters.monster_formatter import MonsterFormatter
import grimbrain.formatters.monster_formatter as monster_formatter


def test_actions_no_statblock_echo(monkeypatch):
    raw = (
        "Goblin\n"
        "Armor Class 15\n"
        "Hit Points 7 (2d6)\n"
        "Speed 30 ft.\n"
        "\n"
        "Scimitar. Melee Weapon Attack: +4 to hit...\n"
        "Scimitar. Melee Weapon Attack: +4 to hit...\n"
        "Shortbow. Ranged Weapon Attack: +4 to hit...\n"
    )
    monkeypatch.setattr(monster_formatter, "maybe_stitch_monster_actions", lambda *a, **k: raw)
    fmt = MonsterFormatter()
    out = fmt.format(raw, {})
    actions = out.split("**Actions**", 1)[1]
    assert "Armor Class" not in actions
    assert actions.count("Scimitar") == 1
