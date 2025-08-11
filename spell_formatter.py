import re
from utils import coerce_obj, ordinal

class SpellFormatter:
    def __init__(self, raw_text:str|None=None, metadata:dict|None=None):
        self.raw_text = raw_text or ""
        self.metadata = metadata or {}

    # -- helpers -------------------------------------------------------------
    def _school_full(self, school: str | None) -> str:
        """Return a human-friendly school name.
        Uses the new utils method if available; otherwise falls back to a local map/title."""
        if school is None:
            return ""
        try:
            # Prefer your new utility if present (e.g., utils.school_name or utils.school_long_name)
            from utils import school_name  # type: ignore
            return str(school_name(school)).strip()
        except Exception:
            try:
                from utils import school_long_name  # type: ignore
            except Exception:
                school_long_name = None
            if callable(school_long_name):
                try:
                    return str(school_long_name(school)).strip()
                except Exception:
                    pass
        # Fallbacks
        MAP = {
            "A": "Abjuration",
            "C": "Conjuration",
            "D": "Divination",
            "EN": "Enchantment",
            "I": "Illusion",
            "N": "Necromancy",
            "T": "Transmutation",
            "V": "Evocation",
        }
        s = str(school).strip()
        upper = s.upper()
        if upper in MAP:
            return MAP[upper]
        return s.title()

    def _level_school_header(self, level, school) -> str:
        """Render the markdown header, e.g. `_3rd-level Evocation_` or `_Cantrip Evocation_`."""
        school_full = self._school_full(school)
        try:
            lvl_i = int(level) if level is not None else None
        except Exception:
            lvl_i = None
        if lvl_i == 0:
            return f"_Cantrip {school_full}_" if school_full else "_Cantrip_"
        if lvl_i is not None:
            return f"_{ordinal(lvl_i)}-level {school_full}_" if school_full else f"_{ordinal(lvl_i)}-level_"
        # Unknown level; show school only if we have it.
        return f"_{school_full}_" if school_full else ""

    def format(self, raw_text:str|None=None, metadata:dict|None=None)->str:
        text = (raw_text or self.raw_text or "").strip()
        md = metadata or self.metadata or {}

        name = md.get("name") or (text.splitlines()[0] if text else "Unknown Spell")
        level = md.get("level")
        school = md.get("school","")
        lvl_line = f"{ordinal(level)} {_fmt_school(school)}"

        r     = _fmt_range(coerce_obj(md.get("range")))
        comps = _fmt_components(coerce_obj(md.get("components")))
        dur   = _fmt_duration(coerce_obj(md.get("duration")))
        time  = _fmt_time(coerce_obj(md.get("casting_time")))

        # try to extract a damage expression if metadata was "Unknown"
        damage = md.get("damage")
        if not damage or damage == "Unknown":
            damage = _extract_damage(text)

        header = f"🔥 **{name}**\n_{lvl_line}_\n"
        lines = [
            f"**Range:** {r}",
            f"**Components:** {comps}",
            f"**Duration:** {dur}",
            f"**Casting Time:** {time}",
        ]
        if damage:
            lines.insert(0, f"**Damage:** {damage}")

        # Header line via helper that uses the new utils method when available
        header = self._level_school_header(level, school)
        # Normalize header to ensure "-level" is present for numbered levels
        if header:
            header = re.sub(r"^_(\d+)(st|nd|rd|th)\s+", r"_\1\2-level ", header)
        if header:
            lines.append(header)

        body = "\n".join(lines)
        return f"{header}{body}"
    
_SCHOOL_MAP = {
    "A":"Abjuration","C":"Conjuration","D":"Divination","EN":"Enchantment",
    "EV":"Evocation","I":"Illusion","N":"Necromancy","T":"Transmutation",
    # 2014/2024 sources sometimes use single letters (PHB) or two letters (XPHB)
    "V":"Evocation"  # your data shows V; treat it as Evocation
}

def _fmt_school(abbrev:str)->str:
    if not abbrev: return ""
    a = abbrev.upper()
    return _SCHOOL_MAP.get(a, a.title())

def _fmt_distance(d):
    if isinstance(d, dict):
        amt = d.get("amount")
        unit = d.get("type","").replace("_"," ")
        if amt is not None and unit:
            return f"{amt} {unit}"
    elif isinstance(d, (int,float,str)):
        return str(d)
    return None

def _fmt_range(r):
    # 5eTools range objects vary; handle common cases
    if isinstance(r, dict):
        t = r.get("type")
        dist = r.get("distance")
        dist_s = _fmt_distance(dist)
        if t in ("point","line","cone","cube","sphere","cylinder"):
            shape = t if t != "point" else ""
            if isinstance(dist, dict) and dist.get("type") in ("feet","foot","ft"):
                dist_s = f"{dist.get('amount', dist_s)} feet"
            return (shape + (" " if shape and dist_s else "") + (dist_s or "")).strip() or "—"
        if t == "self":
            if isinstance(dist, dict):
                # e.g. {type:'self', distance:{type:'radius', amount:10, distance:{type:'feet', amount:10}}}
                inner = _fmt_distance(dist) or ""
                return f"Self{(' ('+inner+')') if inner else ''}"
            return "Self"
        if t == "touch": return "Touch"
        if dist_s: return dist_s
    elif isinstance(r, list):
        return ", ".join(_fmt_range(x) for x in r)
    elif r:
        return str(r)
    return "—"

def _fmt_components(c):
    if isinstance(c, dict):
        parts = []
        if c.get("v"): parts.append("V")
        if c.get("s"): parts.append("S")
        m = c.get("m")
        if m:
            mat = m if isinstance(m, str) else ""
            parts.append(f"M ({mat})" if mat else "M")
        return ", ".join(parts) or "—"
    if isinstance(c, list): return ", ".join(map(str,c))
    return str(c) if c else "—"

def _fmt_duration(d):
    # usually a list; handle first item
    def one(x):
        if isinstance(x, dict):
            t = x.get("type")
            if t == "instant": return "Instantaneous"
            if t == "permanent": return "Permanent"
            if t == "timed":
                dur = x.get("duration", x)
                if isinstance(dur, dict):
                    amt = dur.get("amount")
                    unit = dur.get("type","").replace("_"," ")
                    conc = x.get("concentration")
                    base = f"{amt} {unit}" if amt and unit else unit or "—"
                    return f"Concentration, up to {base}" if conc else base
        return str(x)
    if isinstance(d, list) and d: return one(d[0])
    return one(d) if d else "—"

def _fmt_time(t):
    def one(x):
        if isinstance(x, dict):
            num = x.get("number", 1)
            unit = x.get("unit","").replace("_"," ")
            return f"{num} {unit}".strip()
        return str(x)
    if isinstance(t, list) and t: return one(t[0])
    return one(t) if t else "—"

_DAMAGE_RE = re.compile(r"\{@damage\s+([^}]+)\}", re.IGNORECASE)

def _extract_damage(text: str) -> str | None:
    if not text:
        return None
    m = _DAMAGE_RE.search(text)
    if not m:
        return None
    dice = m.group(1).strip()
    tail = text[m.end() : m.end() + 40].lower()
    m2 = re.search(r"\b(\w+)\s+damage", tail)
    return f"{dice} {m2.group(1)}" if m2 else dice


def spell_to_json(markdown: str, meta: dict | None = None) -> dict:
    """Parse formatted spell markdown into a structured dict."""
    meta = meta or {}
    lines = [ln.strip() for ln in markdown.splitlines()]

    def grab(label: str) -> str:
        pat = re.compile(rf"^\*\*{re.escape(label)}:?\*\*\s*(.+)$", re.IGNORECASE)
        for ln in lines:
            m = pat.match(ln)
            if m:
                return m.group(1).strip()
        return ""

    name = meta.get("name") or ""
    if not name and lines:
        m = re.search(r"\*\*(.+?)\*\*", lines[0])
        if m:
            name = m.group(1).strip()

    level = meta.get("level")
    school = meta.get("school") or ""
    header = next((ln for ln in lines if ln.startswith("_") and ln.endswith("_")), "")
    if level is None:
        m = re.search(r"(\d+)", header)
        if m:
            try:
                level = int(m.group(1))
            except Exception:
                level = None
    if not school:
        m = re.search(r"-level\s+(.*)", header)
        if m:
            school = m.group(1).strip()

    casting_time = grab("Casting Time") or _fmt_time(coerce_obj(meta.get("casting_time")))
    range_ = grab("Range") or _fmt_range(coerce_obj(meta.get("range")))
    components = grab("Components") or _fmt_components(coerce_obj(meta.get("components")))
    duration = grab("Duration") or _fmt_duration(coerce_obj(meta.get("duration")))

    classes = meta.get("classes") or meta.get("class") or []
    if isinstance(classes, str):
        classes = [c.strip() for c in classes.split(",") if c.strip()]

    text = meta.get("text") or markdown
    provenance = meta.get("provenance") or []

    try:
        level = int(level) if level is not None else None
    except Exception:
        level = None

    return {
        "name": name,
        "level": level,
        "school": _fmt_school(str(school)) if school else "",
        "casting_time": casting_time or "",
        "range": range_ or "",
        "components": components or "",
        "duration": duration or "",
        "classes": classes,
        "text": text,
        "provenance": provenance,
    }
