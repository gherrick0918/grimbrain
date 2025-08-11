import re
from .spell_formatter import SpellFormatter, spell_to_json
from .monster_formatter import MonsterFormatter, monster_to_json
from .generic_formatter import GenericFormatter
from .item_formatter import ItemFormatter, item_to_json
from .rule_formatter import RuleFormatter, rule_to_json

SCHOOL_MAP = {
    "V": "Evocation",
    "A": "Abjuration",
    "C": "Conjuration",
    "D": "Divination",
    "E": "Enchantment",
    "I": "Illusion",
    "N": "Necromancy",
    "T": "Transmutation",
}

def format_spell_output(text: str) -> str:
    return SpellFormatter(text).format()

def safe_format_field(value):
    if isinstance(value, dict):
        return ", ".join(f"{k}: {v}" for k, v in value.items())
    if isinstance(value, list):
        return "; ".join(safe_format_field(v) for v in value)
    return str(value)

def debug_output(text: str) -> str:
    return f"=== RAW ===\n{text}\n============"

def format_monster_output(text: str) -> str:
    return MonsterFormatter(text).format()

def format_item_output(text: str) -> str:
    return ItemFormatter().format(text)

def format_rule_output(text: str) -> str:
    return RuleFormatter().format(text)

def format_generic_output(text: str) -> str:
    return GenericFormatter(text).format()

def _format_with(FormatterCls, raw_text, metadata):
    try:
        return FormatterCls().format(raw_text, metadata)
    except TypeError:
        try:
            return FormatterCls(raw_text, metadata).format()
        except TypeError:
            return FormatterCls(raw_text).format()

def _append_provenance(out: str, meta: dict) -> str:
    prov = meta.get("provenance") or []
    if not prov:
        return out
    bits = []
    for m in prov[:3]:
        src = m.get("source") or "?"
        nm = m.get("name") or "?"
        bits.append(f"{src} · {nm}")
    return out + "\n\n---\n_Sources considered:_ " + " ; ".join(bits)

def auto_format(raw_text: str, metadata: dict | None = None) -> str:
    """Heuristically format based on content."""
    metadata = metadata or {}
    low = raw_text.lower()
    if ("casting time" in low and "components" in low) or ("spell attack" in low and "components" in low):
        out = _format_with(SpellFormatter, raw_text, metadata)
        return _append_provenance(out, metadata)
    has_ac = ("armor class" in low) or bool(re.search(r"\bac\s*:", low))
    has_hp = ("hit points" in low) or bool(re.search(r"\bhp\s*:", low))
    has_spd = ("speed" in low)
    has_abil = bool(
        re.search(r"\bSTR\s+\d+\s*\([^)]+\)\s*DEX\s+\d+\s*\([^)]+\)\s*CON\s+\d+", raw_text, re.I)
        or re.search(r"\bSTR\s*:\s*\d+.*CHA\s*:\s*\d+", raw_text, re.I)
    )
    looks_monster = (has_ac and has_hp and has_spd) or has_abil
    if looks_monster:
        out = _format_with(MonsterFormatter, raw_text, metadata)
        return _append_provenance(out, metadata)
    out = _format_with(GenericFormatter, raw_text.strip(), metadata)
    return _append_provenance(out, metadata)
