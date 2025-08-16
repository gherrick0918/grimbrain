import json
from pathlib import Path

from grimbrain.rules.resolver import RuleResolver
from grimbrain.rules import index


def _build(chroma):
    index.build_index("rules", chroma)


def test_reload_clears_cache(tmp_path):
    chroma = tmp_path / "chroma"
    _build(chroma)
    res = RuleResolver(rules_dir="rules", chroma_dir=chroma)
    rule, _ = res.resolve("swing")
    assert rule is None

    # mutate rule to include new alias
    path = Path("rules/custom/attack.json")
    orig = path.read_text()
    data = json.loads(orig)
    data["aliases"].append("swing")
    path.write_text(json.dumps(data))
    _build(chroma)

    # Without reload, cached miss remains
    rule, _ = res.resolve("swing")
    assert rule is None

    res.reload()
    rule, _ = res.resolve("swing")
    assert rule and rule["id"] == "attack"

    path.write_text(orig)  # restore
    _build(chroma)
