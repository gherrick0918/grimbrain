from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as pkg_version
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    KeepInFrame,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from grimbrain.models.pc import ABILITY_ORDER, PlayerCharacter
from grimbrain.rules.attacks import format_mod
from grimbrain.rules.defense import compute_ac
from grimbrain.codex.armor import ArmorIndex
SMALL = 9
NORMAL = 10
HEADER = 14

BASE_PATH = Path(__file__).resolve().parent.parent
ARMOR_INDEX = ArmorIndex.load(BASE_PATH / "data" / "armor.json")


def _abilities_table(pc: PlayerCharacter) -> Table:
    data = [["Ability", "Score", "Mod"]]
    for a in ABILITY_ORDER:
        score = getattr(pc.abilities, a)
        mod = pc.ability_mod(a)
        data.append([a.upper(), str(score), format_mod(mod)])
    t = Table(data, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", NORMAL),
                ("FONT", (0, 1), (-1, -1), "Helvetica", NORMAL),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (1, 1), (-1, -1), "CENTER"),
            ]
        )
    )
    return t


def _caps_csv(items: Iterable[str]) -> str:
    return ", ".join(s.upper() for s in sorted(items)) if items else "—"


def _slots_line(pc: PlayerCharacter, show_zero: bool) -> str:
    parts: list[str] = []
    if pc.spell_slots:
        for i in range(1, 10):
            v = getattr(pc.spell_slots, f"l{i}")
            if v or show_zero:
                parts.append(f"L{i}:{v}")
    return ", ".join(parts) if parts else "—"


def _pkg_version() -> str:
    try:
        return pkg_version("grimbrain")
    except PackageNotFoundError:  # pragma: no cover - local checkout
        return "0.0"


def _profs_table(pc: PlayerCharacter) -> Table:
    saves = _caps_csv(pc.save_proficiencies)
    skills = _caps_csv(pc.skill_proficiencies)
    langs = ", ".join(pc.languages) if pc.languages else "—"
    tools = ", ".join(pc.tool_proficiencies) if pc.tool_proficiencies else "—"
    data = [
        ["Prof. Bonus", format_mod(pc.prof)],
        ["Saves", saves],
        ["Skills", skills],
        ["Languages", langs],
        ["Tools", tools],
    ]
    t = Table(data, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), "Helvetica", NORMAL),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", NORMAL),
            ]
        )
    )
    return t


def _defense_table(pc: PlayerCharacter) -> Table:
    data = [
        [
            "AC",
            str(pc.ac),
            "HP",
            f"{pc.current_hp}/{pc.max_hp}",
            "Init.",
            format_mod(pc.initiative),
            "Passive Perception",
            str(pc.passive_perception),
        ]
    ]
    t = Table(data, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), "Helvetica", NORMAL),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ]
        )
    )
    return t


def _spell_stats_table(pc: PlayerCharacter) -> Table:
    from grimbrain.characters import spell_save_dc, spell_attack_bonus

    dc = spell_save_dc(pc)
    atk = spell_attack_bonus(pc)
    rows = []
    if dc is not None and atk is not None:
        rows.append(["Spell Save DC", str(dc)])
        rows.append(["Spell Attack", format_mod(atk)])
    else:
        rows.append(["Spellcasting", "—"])
    t = Table(rows, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), "Helvetica", NORMAL),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", NORMAL),
            ]
        )
    )
    return t


def _slots_table(pc: PlayerCharacter, show_zero: bool) -> Table:
    data = [["Slots", _slots_line(pc, show_zero)]]
    t = Table(data, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), "Helvetica", NORMAL),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", NORMAL),
            ]
        )
    )
    return t


def _prepared_table(pc: PlayerCharacter) -> Table:
    items = ", ".join(pc.prepared_spells) if pc.prepared_spells else "—"
    t = Table([["Prepared", items]], hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), "Helvetica", NORMAL),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", NORMAL),
            ]
        )
    )
    return t


def _inventory_table(pc: PlayerCharacter) -> Table:
    rows = [["Item", "Qty", "Props"]]
    if not pc.inventory:
        rows.append(["—", "—", "—"])
    else:
        for it in pc.inventory:
            props = (
                ", ".join(f"{k}={v}" for k, v in (it.props or {}).items())
                if it.props
                else ""
            )
            rows.append([it.name, str(it.qty or 1), props])
    t = Table(rows, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", NORMAL),
                ("FONT", (0, 1), (-1, -1), "Helvetica", NORMAL),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
            ]
        )
    )
    return t


def save_pdf(
    pc: PlayerCharacter,
    path: Path,
    meta: dict[str, str] | None = None,
    logo: Path | None = None,
    show_zero_slots: bool = False,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(path),
        pagesize=letter,
        leftMargin=44,
        rightMargin=44,
        topMargin=36,
        bottomMargin=36,
    )
    styles = getSampleStyleSheet()

    title_text = f"<b>{pc.name}</b> — {pc.class_}{f' ({pc.subclass})' if pc.subclass else ''}  L{pc.level}"
    title_para = Paragraph(title_text, styles["Title"])
    ac_info = compute_ac(pc, ARMOR_INDEX)
    parts = ", ".join(ac_info["components"])
    notes = "; ".join(ac_info["notes"]) if ac_info["notes"] else ""
    ac_line = f"AC {ac_info['ac']} — {parts}"
    if notes:
        ac_line += f"; {notes}"
    ac_para = Paragraph(ac_line, styles["Normal"])
    if logo and logo.exists():
        img = Image(str(logo))
        img._restrictSize(1.2 * inch, 1.2 * inch)
        header = Table([[img, title_para]], colWidths=[1.3 * inch, None], hAlign="LEFT")
    else:
        header = Table([[title_para]], colWidths=[None], hAlign="LEFT")

    left = [
        Paragraph("<b>Abilities</b>", styles["Heading3"]),
        _abilities_table(pc),
        Spacer(1, 0.12 * inch),
        Paragraph("<b>Proficiencies</b>", styles["Heading3"]),
        _profs_table(pc),
        Spacer(1, 0.12 * inch),
        Paragraph("<b>Defense</b>", styles["Heading3"]),
        _defense_table(pc),
    ]
    right = [
        Paragraph("<b>Spellcasting</b>", styles["Heading3"]),
        _spell_stats_table(pc),
        Spacer(1, 0.08 * inch),
        _slots_table(pc, show_zero_slots),
        Spacer(1, 0.08 * inch),
        _prepared_table(pc),
        Spacer(1, 0.12 * inch),
        Paragraph("<b>Inventory</b>", styles["Heading3"]),
        _inventory_table(pc),
    ]

    col_width = 3.4 * inch
    left_tbl = Table([[x] for x in left], hAlign="LEFT")
    right_tbl = Table([[x] for x in right], hAlign="LEFT")

    left_fit = KeepInFrame(col_width, 9 * inch, [left_tbl], mode="shrink")
    right_fit = KeepInFrame(col_width, 9 * inch, [right_tbl], mode="shrink")

    body = Table([[left_fit, right_fit]], colWidths=[col_width, col_width])
    body.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))

    meta = meta or {}
    meta.setdefault("version", _pkg_version())
    meta.setdefault("generated", datetime.utcnow().isoformat() + "Z")
    footer_text = "  •  ".join(f"{k.upper()}: {v}" for k, v in meta.items())
    footer = Paragraph(
        f"<font size=9 color=grey>{footer_text}</font>", styles["Normal"]
    )

    doc.build([header, ac_para, Spacer(1, 0.15 * inch), body, Spacer(1, 0.2 * inch), footer])
