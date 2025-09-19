from dataclasses import asdict
from typing import Dict
from pathlib import Path
import json

from .campaign import PartyMemberRef


HIT_DICE = {
    "fighter": 10,
    "rogue": 8,
    "wizard": 6,
}

STANDARD_ARRAY = [15, 14, 13, 12, 10, 8]
ABILS = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]


def ability_mod(score: int) -> int:
    return (score - 10) // 2


def _point_buy_cost(scores: Dict[str, int]) -> int:
    """Return the total point-buy cost for a mapping of ability scores."""

    cost_table = {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}
    total = 0
    for ability, value in scores.items():
        if value < 8 or value > 15:
            raise ValueError(f"{ability} score {value} out of point-buy bounds 8..15")
        total += cost_table[value]
    return total


def _parse_scores_from_array(array_csv: str) -> Dict[str, int]:
    values = [int(x.strip()) for x in array_csv.split(",")]
    if len(values) != 6:
        raise ValueError("Expected 6 comma-separated scores for --array")
    values_sorted = sorted(values, reverse=True)
    return dict(zip(ABILS, values_sorted))


def _parse_scores_from_kv(kv: str) -> Dict[str, int]:
    """
    Accepts either:
      - "STR=10 DEX=15 CON=14 INT=12 WIS=10 CHA=8" (space-separated)
      - "STR=10,DEX=15,CON=14,INT=12,WIS=10,CHA=8" (comma-separated)
    """

    results: Dict[str, int] = {}
    tokens: list[str] = []
    for chunk in kv.split(","):
        tokens.extend(chunk.strip().split())

    for pair in tokens:
        if "=" not in pair:
            continue
        key, value = pair.split("=", 1)
        key = key.strip().upper()
        results[key] = int(value)

    for ability in ABILS:
        if ability not in results:
            raise ValueError(f"Missing {ability} in scores (have {sorted(results)})")

    return results


def build_partymember(
    name: str,
    cls: str,
    scores: Dict[str, int],
    weapon: str,
    ranged: bool,
    pb: int = 2,
) -> PartyMemberRef:
    cls_l = cls.lower()
    hit_die = HIT_DICE.get(cls_l, 8)
    mods = {ability.lower() + "_mod": ability_mod(scores[ability]) for ability in ABILS}
    ac = 10 + max(0, mods["dex_mod"])
    max_hp = hit_die + mods["con_mod"]
    if max_hp < 1:
        max_hp = 1
    return PartyMemberRef(
        id=name,
        name=name,
        pb=pb,
        speed=30,
        ac=ac,
        max_hp=max_hp,
        weapon_primary=weapon,
        ranged=ranged,
        **mods,
    )


def save_pc(pc: PartyMemberRef, out_path: str) -> None:
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(pc), indent=2), encoding="utf-8")


def load_pc(path: str) -> PartyMemberRef:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return PartyMemberRef(**data)
