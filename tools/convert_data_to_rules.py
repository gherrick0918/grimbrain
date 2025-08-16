"""Convert source data into rule JSON files.

This script reads ``data/weapons.json`` and ``data/spells.json`` and emits
rule-shaped JSON documents under ``rules/generated``.  The generator is
idempotent and uses atomic writes so repeated runs are safe.  Missing source
files are ignored.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Tuple

DATA_WEAPONS = Path("data/weapons.json")
DATA_SPELLS = Path("data/spells.json")
GENERATED_DIR = Path("rules/generated")


def slugify(text: str) -> str:
    """Return a filesystem-safe slug."""

    slug = re.sub(r"[^a-z0-9]+", ".", text.lower())
    return slug.strip(".")


def atomic_write(path: Path, content: str) -> None:
    """Write ``content`` to ``path`` atomically."""

    tmp = path.with_suffix(path.suffix + ".tmp")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(content)
    tmp.replace(path)


def _weapon_rules(data: Iterable[dict]) -> Iterable[Tuple[str, dict]]:
    for w in data:
        name = w.get("name")
        if not name:
            print("Skipping weapon without name", file=sys.stderr)
            continue
        slug = slugify(name)
        rid = f"attack.{slug}"
        rng = (w.get("range") or w.get("type") or "").lower()
        melee = not rng.startswith("r")
        props = [p.lower() for p in w.get("properties", w.get("property", []))]
        finesse = "finesse" in props or "fin" in props
        dmg_dice = w.get("damage_dice") or w.get("damage")
        dmg_type = w.get("damage_type") or "slashing"
        rule: dict[str, Any] = {
            "id": rid,
            "kind": "action",
            "subkind": "melee" if melee else "ranged",
            "cli_verb": "attack",
            "aliases": [name],
            "targets": ["target"],
            "effects": [],
            "log_templates": {
                "start": "{actor.name} attacks {target.name}",
                "apply": "{actor.name} hits {target.name} for {last_amount} {damage_type}",
            },
            "metadata": {"source_path": str(DATA_WEAPONS)},
        }
        if dmg_dice:
            mod = "{mod.DEX}" if (not melee or finesse) else "{mod.STR}"
            rule["formulas"] = {"amount": f"{dmg_dice} + {mod}"}
            rule["effects"].append(
                {
                    "op": "damage",
                    "target": "target",
                    "amount": "{amount}",
                    "damage_type": dmg_type or "slashing",
                }
            )
        yield rid, rule


def _spell_rules(data: Iterable[dict]) -> Iterable[Tuple[str, dict]]:
    for s in data:
        name = s.get("name")
        if not name:
            print("Skipping spell without name", file=sys.stderr)
            continue
        slug = slugify(name)
        rid = f"spell.{slug}"
        level = int(s.get("level", 0) or 0)
        dmg_dice = s.get("damage_dice")
        dmg_type = s.get("damage_type") or "force"
        concentration = bool(s.get("concentration"))
        school = s.get("school")
        has_damage = bool(dmg_dice)
        rule: dict[str, Any] = {
            "id": rid,
            "kind": "spell",
            "subkind": "attack" if has_damage else "utility",
            "cli_verb": "cast",
            "aliases": [name],
            "targets": ["target"],
            "effects": [],
            "log_templates": {
                "start": f"{{actor.name}} casts {name} at {{target.name}}",
                "apply": "{target.name} takes {last_amount} {damage_type}",
            },
            "metadata": {"school": school, "level": level},
        }
        if level > 0:
            rule["effects"].append(
                {
                    "op": "resource_spend",
                    "resource": f"spell_slots.{level}",
                    "amount": 1,
                }
            )
        if concentration:
            rule["effects"].append({"op": "concentration_start"})
        if dmg_dice:
            rule["effects"].append(
                {
                    "op": "damage",
                    "target": "target",
                    "amount": dmg_dice,
                    "damage_type": dmg_type or "force",
                }
            )
        yield rid, rule


def convert() -> int:
    rules: list[Tuple[str, dict]] = []
    if DATA_WEAPONS.exists():
        weapons = json.loads(DATA_WEAPONS.read_text())
        print(f"Loaded {len(weapons)} weapons")
        rules.extend(_weapon_rules(weapons))
    else:
        print("No weapons.json found", file=sys.stderr)
    if DATA_SPELLS.exists():
        spells = json.loads(DATA_SPELLS.read_text())
        print(f"Loaded {len(spells)} spells")
        rules.extend(_spell_rules(spells))
    else:
        print("No spells.json found", file=sys.stderr)

    potion_rule = {
        "id": "item.potion.healing",
        "kind": "item",
        "cli_verb": "use",
        "targets": ["self"],
        "effects": [
            {"op": "heal", "target": "self", "amount": "2d4+2"},
            {"op": "clear_death_saves", "target": "self"},
        ],
        "log_templates": {
            "apply": "{actor.name} regains {last_amount} HP (Potion of Healing)"
        },
    }
    rules.append((potion_rule["id"], potion_rule))

    for rid, rule in rules:
        out_path = GENERATED_DIR / f"{rid}.json"
        content = json.dumps(rule, indent=2, sort_keys=True)
        atomic_write(out_path, content)
    return 0


def main() -> int:
    return convert()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
