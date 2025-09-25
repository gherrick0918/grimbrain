from dataclasses import asdict
from typing import Any, Dict, List, Set
from pathlib import Path
import json
import random

from .campaign import PartyMemberRef
from .srd import find_armor, find_shield, load_srd


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


def apply_asi(base_scores: Dict[str, int], asi_list: List[Dict[str, object]]) -> Dict[str, int]:
    """Return ability scores with ability score increases applied."""

    updated = dict(base_scores)
    for asi in asi_list or []:
        ability = str(asi.get("ability", "")).upper()
        if not ability:
            continue
        bonus = int(asi.get("bonus", 0))
        updated[ability] = updated.get(ability, 10) + bonus
    return updated


def merge_unique(a: List[str] | Set[str] | None, b: List[str] | Set[str] | None) -> List[str]:
    """Merge two iterables into a sorted list of unique strings."""

    items: Set[str] = set(a or [])
    items.update(b or [])
    return sorted(items)


def build_partymember(
    name: str,
    cls: str,
    scores: Dict[str, int],
    weapon: str,
    ranged: bool,
    pb: int = 2,
    armor: str | None = None,
    shield: bool = False,
    prof_skills: List[str] | None = None,
    prof_saves: List[str] | None = None,
    *,
    race: str | None = None,
    background: str | None = None,
    languages: List[str] | None = None,
    tool_profs: List[str] | None = None,
    features: Dict[str, Any] | None = None,
) -> PartyMemberRef:
    cls_l = cls.lower()
    hit_die = HIT_DICE.get(cls_l, 8)
    mods = {ability.lower() + "_mod": ability_mod(scores[ability]) for ability in ABILS}
    ac = 10 + max(0, mods["dex_mod"])
    stealth_disadv = False
    armor_name: str | None = None
    try:
        srd = load_srd()
    except FileNotFoundError:
        srd = None
    if armor and srd:
        armor_obj = find_armor(armor, srd)
        if not armor_obj:
            known = ", ".join(sorted(srd.armors))
            raise ValueError(f"Unknown armor '{armor}'. Known: {known}")
        dex_bonus = mods["dex_mod"]
        if armor_obj.dex_cap is not None:
            dex_bonus = min(dex_bonus, armor_obj.dex_cap)
        ac = armor_obj.base_ac + max(0, dex_bonus)
        stealth_disadv = armor_obj.stealth_disadv
        armor_name = armor_obj.name
    elif armor:
        armor_name = armor
    if shield and srd:
        shield_obj = find_shield("Shield", srd)
        if not shield_obj:
            raise ValueError("Shield data missing from SRD cache")
        ac += shield_obj.ac_bonus
    elif shield:
        ac += 2
    max_hp = hit_die + mods["con_mod"]
    if max_hp < 1:
        max_hp = 1
    prof_skills_set = sorted(set(prof_skills or []))
    prof_saves_set = sorted(set(prof_saves or []))
    has_athletics = "Athletics" in prof_skills_set
    has_acrobatics = "Acrobatics" in prof_skills_set
    feature_data: Dict[str, Any] = {}
    if features:
        for key, value in features.items():
            if isinstance(value, list):
                feature_data[key] = list(value)
            elif isinstance(value, dict):
                feature_data[key] = dict(value)
            else:
                feature_data[key] = value

    return PartyMemberRef(
        id=name,
        name=name,
        pb=pb,
        speed=30,
        ac=ac,
        max_hp=max_hp,
        weapon_primary=weapon,
        ranged=ranged,
        armor=armor_name,
        shield=bool(shield),
        stealth_disadv=stealth_disadv,
        prof_skills=prof_skills_set,
        prof_saves=prof_saves_set,
        race=race,
        background=background,
        languages=sorted(languages or []),
        tool_profs=sorted(tool_profs or []),
        features=feature_data,
        prof_athletics=has_athletics,
        prof_acrobatics=has_acrobatics,
        **mods,
    )


def save_pc(pc: PartyMemberRef, out_path: str) -> None:
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(pc), indent=2), encoding="utf-8")


def load_pc(path: str) -> PartyMemberRef:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return PartyMemberRef(**data)


def roll_4d6_drop_lowest(rng: random.Random) -> int:
    dice = sorted([rng.randint(1, 6) for _ in range(4)], reverse=True)
    return sum(dice[:3])


def roll_abilities(seed: int | None = None) -> List[int]:
    """Roll 4d6 drop lowest, six times, returning descending scores."""

    rng = random.Random(seed)
    rolls = [roll_4d6_drop_lowest(rng) for _ in range(6)]
    return sorted(rolls, reverse=True)


def scores_from_list_desc(desc_scores: List[int]) -> Dict[str, int]:
    if len(desc_scores) != 6:
        raise ValueError("Need 6 scores")
    return dict(zip(ABILS, list(desc_scores)))


def pc_summary_line(
    name: str, cls: str, scores: Dict[str, int], weapon: str, ranged: bool
) -> str:
    arr = "/".join(str(scores[key]) for key in ABILS)
    suffix = " (ranged)" if ranged else ""
    return f"{name} the {cls} [{arr}] w/ {weapon}{suffix}"
