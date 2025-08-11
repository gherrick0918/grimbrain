from item_formatter import ItemFormatter, item_to_json
from rule_formatter import RuleFormatter, rule_to_json

def test_item_to_json():
    meta = {"name": "Sword", "type": "Weapon", "rarity": "Common", "text": "A sharp blade."}
    md = ItemFormatter().format("", meta)
    js = item_to_json(md, meta)
    assert js["name"] == "Sword"
    assert js["rarity"] == "Common"


def test_rule_to_json():
    meta = {"name": "Flanking", "category": "Combat", "text": "Gain advantage."}
    md = RuleFormatter().format("", meta)
    js = rule_to_json(md, meta)
    assert js["category"] == "Combat"
