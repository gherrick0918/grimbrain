import json
import os
import subprocess
import sys
from pathlib import Path

from grimbrain.rules.resolver import RuleResolver
from grimbrain.rules import index


def _build_index(tmp_path: Path) -> Path:
    out = tmp_path / "chroma"
    index.build_index("rules", out)
    return out


def test_resolver_exact_and_suggestion(tmp_path):
    chroma = _build_index(tmp_path)
    res = RuleResolver(rules_dir="rules", chroma_dir=chroma)
    rule, _ = res.resolve("attack")
    assert rule and rule["id"] == "attack"
    rule2, _ = res.resolve("atk")
    assert rule2 and rule2["id"] == "attack"
    rule3, sugg = res.resolve("bogus")
    assert rule3 is None


def test_cli_show(tmp_path):
    chroma = _build_index(tmp_path)
    env = os.environ | {"GB_ENGINE": "data", "GB_RULES_DIR": "rules", "GB_CHROMA_DIR": str(chroma)}
    out = subprocess.check_output([sys.executable, "main.py", "rules", "show", "attack"], env=env, text=True)
    data = json.loads(out)
    assert data["id"] == "attack"
