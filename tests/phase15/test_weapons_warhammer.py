import json
from pathlib import Path


def test_warhammer_present_in_weapons():
    data = json.loads(Path("data/weapons.json").read_text(encoding="utf-8"))
    warhammer_entries = [w for w in data if w.get("name", "").lower() == "warhammer"]
    assert warhammer_entries, "Warhammer weapon entry missing"
    entry = warhammer_entries[0]
    assert entry["damage"] == "1d8"
    assert any(prop.startswith("versatile") for prop in entry.get("properties", []))
