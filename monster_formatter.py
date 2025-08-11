# formatters/monster_formatter.py
import re
from typing import Dict, Any, Tuple
from utils import maybe_stitch_monster_actions

# --- optional debug logger (no-op if utils._log isn't available) ---
try:
    from utils import _log as _utils_log  # type: ignore
    def _log(msg: str) -> None:
        try:
            _utils_log(msg)
        except Exception:
            pass
except Exception:
    def _log(msg: str) -> None:  # noqa: D401
        # quiet fallback
        pass

ABILITY_RE = re.compile(
    r"\bSTR\s+(\d+)\s*\([^)]+\)\s*DEX\s+(\d+)\s*\([^)]+\)\s*CON\s+(\d+)\s*\([^)]+\)\s*"
    r"INT\s+(\d+)\s*\([^)]+\)\s*WIS\s+(\d+)\s*\([^)]+\)\s*CHA\s+(\d+)\s*\([^)]+\)",
    re.IGNORECASE | re.MULTILINE | re.DOTALL,
)
ABILITY_COLON_RE = re.compile(
    r"\bSTR\s*:\s*(\d+)\s*,\s*DEX\s*:\s*(\d+)\s*,\s*CON\s*:\s*(\d+)\s*,\s*"
    r"INT\s*:\s*(\d+)\s*,\s*WIS\s*:\s*(\d+)\s*,\s*CHA\s*:\s*(\d+)\b",
    re.IGNORECASE | re.MULTILINE | re.DOTALL,
)

SECTION_HEADS = [
    "Armor Class", "Hit Points", "Speed", "Saving Throws", "Skills",
    "Damage Immunities", "Damage Resistances", "Damage Vulnerabilities",
    "Condition Immunities", "Senses", "Languages", "Challenge",
    "Proficiency Bonus",
]

def _find(key: str, text: str) -> str:
    m = re.search(rf"{re.escape(key)}\s*[:]\s*([^\n]+)", text, re.IGNORECASE)
    return m.group(1).strip() if m else ""

def _find_any(keys: list[str], text: str) -> str:
    for k in keys:
        v = _find(k, text)
        if v:
            return v
    return ""

def _extract_blocks(text: str) -> Tuple[Dict[str, str], Dict[str, str], Dict[str, str]]:
    # Traits before "Actions", Actions until "Reactions/Legendary"
    # Parse "Name. description" blocks.
    def grab(start_pat, end_pats):
        start = re.search(start_pat, text, re.IGNORECASE)
        if not start:
            return ""
        start_idx = start.end()
        end_idx = len(text)
        for p in end_pats:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                end_idx = min(end_idx, m.start())
        return text[start_idx:end_idx].strip()

    traits_txt = grab(r"\b(?:^|\n)(?=Armor Class|Hit Points|Speed|Saving Throws|Skills|Damage |Condition |Senses|Languages|Challenge|Proficiency Bonus|Actions\b)",
                      [r"\bActions\b", r"\bReactions\b", r"\bLegendary Actions\b"])
    actions_txt = grab(r"\bActions\b", [r"\bReactions\b", r"\bLegendary Actions\b", r"\Z"])
    reactions_txt = grab(r"\bReactions\b", [r"\bLegendary Actions\b", r"\Z"])
    return (
        _named_paras(traits_txt),
        _named_paras(actions_txt),
        _named_paras(reactions_txt),
    )

def _named_paras(block: str) -> Dict[str, str]:
    # Match "Name. desc..." until next "Capword." at BOL or section end.
    items = {}
    if not block:
        return items
    pattern = re.compile(
        r"(?m)^(?P<name>[A-Z][A-Za-z ’'\-()/]+)\.\s*(?P<desc>.*?)(?=^\s*[A-Z][A-Za-z ’'\-()/]+\.\s*|$\Z)",
        re.DOTALL | re.MULTILINE,
    )
    for m in pattern.finditer(block):
        name = m.group("name").strip()
        desc = " ".join(m.group("desc").strip().split())
        if name and desc:
            items[name] = desc
    return items


ATTACK_RE = re.compile(
    r"^(?P<type>Melee|Ranged|Melee or Ranged|Ranged or Melee) Weapon Attack:\s+"
    r"(?P<bonus>[+-]?\d+) to hit,\s+"
    r"(?P<reach>[^,]+),\s+"
    r"(?P<target>[^.]+)\.\s*Hit:\s*(?P<hit>.*)$",
    re.IGNORECASE,
)

DAMAGE_RE = re.compile(r"\((?P<dice>[^)]+)\)\s*(?P<dtype>[A-Za-z]+) damage", re.IGNORECASE)


def _parse_action_struct(name: str, text: str) -> Dict[str, Any] | None:
    m = ATTACK_RE.match(text)
    if not m:
        return None
    atk_type = m.group("type").lower()
    if "ranged" in atk_type and "melee" in atk_type:
        atk_type = "ranged"
    elif "melee" in atk_type:
        atk_type = "melee"
    else:
        atk_type = "ranged"
    bonus = int(m.group("bonus"))
    reach = m.group("reach").strip()
    target = m.group("target").strip()
    hit_text = m.group("hit").strip()
    dmg = DAMAGE_RE.search(hit_text)
    dmg_dice = dmg.group("dice").strip() if dmg else ""
    dmg_type = dmg.group("dtype").strip().lower() if dmg else ""
    return {
        "name": name,
        "attack_bonus": bonus,
        "type": atk_type,
        "reach_or_range": reach,
        "target": target,
        "hit_text": hit_text,
        "damage_dice": dmg_dice,
        "damage_type": dmg_type,
    }

class MonsterFormatter:
    def format(self, text: str, meta: Dict[str, Any] | None = None) -> str:
        meta = meta or {}
        name = (meta.get("name") or "").strip() or self._guess_name(text)
        source = (meta.get("source") or "").strip()

        # Accept both long and short labels (AC/HP). Always render as full labels.
        ac  = _find_any(["Armor Class", "AC"], text)
        hp  = _find_any(["Hit Points", "HP"], text)
        spd = _find_any(["Speed"], text)

        abilities = {}
        m = ABILITY_RE.search(text) or ABILITY_COLON_RE.search(text)
        if m:
            abilities = dict(zip(["STR", "DEX", "CON", "INT", "WIS", "CHA"], m.groups()))

        fields = {k: _find(k, text) for k in SECTION_HEADS[3:]}  # skip AC/HP/Speed here

        traits, actions, reactions = _extract_blocks(text)

        # Markdown (keeps "Armor Class" literal so your tests still pass)
        lines = []
        title = f"### {name}" + (f" — {source}" if source else "")
        lines.append(title)
        lines.append("")
        if ac: lines.append(f"**Armor Class**: {ac}")
        if hp: lines.append(f"**Hit Points**: {hp}")
        if spd: lines.append(f"**Speed**: {spd}")
        if abilities:
            lines.append(
                "**STR** {STR}  **DEX** {DEX}  **CON** {CON}  **INT** {INT}  **WIS** {WIS}  **CHA** {CHA}".format(**abilities)
            )
        for k, v in fields.items():
            if v:
                lines.append(f"**{k}**: {v}")

        if traits:
            lines.append("")
            lines.append("**Traits**")
            for k, v in traits.items():
                lines.append(f"- **{k}.** {v}")

        # Actions section (patched)
        lines.append("")
        lines.append("**Actions**")
        seen: set[str] = set()
        for k, v in actions.items():
            lines.append(f"- **{k}.** {v}")
            seen.add(k)
        if not actions:
            stitched = maybe_stitch_monster_actions(None, text, meta=meta)
            if stitched:
                extra = _named_paras(stitched)
                for k, v in extra.items():
                    if k in seen:
                        continue
                    lines.append(f"- **{k}.** {v}")
                    seen.add(k)
        if len(lines) == 2:  # header only
            lines.append("- _See source entry for full actions text._")

        if reactions:
            lines.append("")
            lines.append("**Reactions**")
            for k, v in reactions.items():
                lines.append(f"- **{k}.** {v}")

        return "\n".join(lines).rstrip()

    def _guess_name(self, text: str) -> str:
        first = (text.strip().splitlines() or [""])[0].strip()
        # Fallback to Title Case of first line if it isn't a labeled section
        if first and not any(h.lower() in first.lower() for h in ["armor class", "hit points", "speed"]):
            return first.strip("# ").strip()
        return "Unknown Creature"


def monster_to_json(markdown: str, meta: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Parse the formatted monster markdown into a structured JSON dict."""
    meta = meta or {}

    lines = [ln.strip() for ln in markdown.splitlines()]
    header_re = re.compile(r"^###\s*(.+?)(?:\s+—\s+(.+))?$")
    abil_re = re.compile(
        r"\*\*STR\*\*\s*(\d+)\s*\*\*DEX\*\*\s*(\d+)\s*\*\*CON\*\*\s*(\d+)\s*"
        r"\*\*INT\*\*\s*(\d+)\s*\*\*WIS\*\*\s*(\d+)\s*\*\*CHA\*\*\s*(\d+)",
        re.IGNORECASE,
    )

    out: Dict[str, Any] = {
        "name": "",
        "source": meta.get("source", ""),
        "ac": "",
        "hp": "",
        "speed": "",
        "str": 0,
        "dex": 0,
        "con": 0,
        "int": 0,
        "wis": 0,
        "cha": 0,
        "traits": [],
        "actions": [],
        "actions_struct": [],
        "reactions": [],
        "provenance": meta.get("provenance", []),
    }

    section: str | None = None
    for line in lines:
        if not line:
            continue
        m = header_re.match(line)
        if m:
            out["name"] = m.group(1).strip()
            if m.group(2):
                out["source"] = m.group(2).strip()
            continue
        if line.startswith("**Armor Class**"):
            out["ac"] = line.split("**Armor Class**:", 1)[1].strip()
            continue
        if line.startswith("**Hit Points**"):
            out["hp"] = line.split("**Hit Points**:", 1)[1].strip()
            continue
        if line.startswith("**Speed**"):
            out["speed"] = line.split("**Speed**:", 1)[1].strip()
            continue
        if line.startswith("**STR**"):
            m2 = abil_re.search(line)
            if m2:
                stats = list(map(int, m2.groups()))
                for k, v in zip(["str", "dex", "con", "int", "wis", "cha"], stats):
                    out[k] = v
            continue
        if line == "**Traits**":
            section = "traits"
            continue
        if line == "**Actions**":
            section = "actions"
            continue
        if line == "**Reactions**":
            section = "reactions"
            continue
        if line.startswith("- **") and section:
            m3 = re.match(r"- \*\*(.+?)\.\*\*\s*(.+)", line)
            if m3:
                getattr_list = out[section]
                action_name = m3.group(1).strip()
                action_text = m3.group(2).strip()
                getattr_list.append({"name": action_name, "text": action_text})
                if section == "actions":
                    parsed = _parse_action_struct(action_name, action_text)
                    if parsed:
                        out["actions_struct"].append(parsed)
            continue

    return out
