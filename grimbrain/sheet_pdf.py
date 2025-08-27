from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from grimbrain.models.pc import ABILITY_ORDER, PlayerCharacter


SMALL = 9
NORMAL = 10
HEADER = 14


def _abilities_table(pc: PlayerCharacter) -> Table:
    data = [["Ability", "Score", "Mod"]]
    for a in ABILITY_ORDER:
        score = getattr(pc.abilities, a)
        mod = pc.ability_mod(a)
        data.append([a.upper(), str(score), f"{mod:+d}"])
    t = Table(data, hAlign="LEFT", colWidths=[1.0 * inch, 0.7 * inch, 0.7 * inch])
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


def _profs_table(pc: PlayerCharacter) -> Table:
    saves = ", ".join(sorted(pc.save_proficiencies)) or "—"
    skills = ", ".join(sorted(pc.skill_proficiencies)) or "—"
    data = [["Prof. Bonus", f"+{pc.prof}"], ["Saves", saves], ["Skills", skills]]
    t = Table(data, hAlign="LEFT", colWidths=[1.2 * inch, 4.3 * inch])
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
            f"{pc.initiative:+d}",
            "Passive Perception",
            str(pc.passive_perception),
        ],
    ]
    t = Table(
        data,
        hAlign="LEFT",
        colWidths=[0.5 * inch, 0.6 * inch, 0.5 * inch, 1.0 * inch, 0.6 * inch, 0.7 * inch, 1.6 * inch, 0.7 * inch],
    )
    t.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), "Helvetica", NORMAL),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("FONT", (0, 0), (-1, -1), "Helvetica", NORMAL),
                ("FONT", (0, 0), (-1, 0), "Helvetica", NORMAL),
            ]
        )
    )
    return t


def _slots_table(pc: PlayerCharacter) -> Table:
    if not pc.spell_slots:
        data = [["Slots", "—"]]
        widths = [0.7 * inch, 5.0 * inch]
    else:
        labels = [f"L{i}" for i in range(1, 10)]
        values = [getattr(pc.spell_slots, f"l{i}") for i in range(1, 10)]
        parts = [f"{l}:{v}" for l, v in zip(labels, values) if v]
        data = [["Slots", ", ".join(parts) if parts else "—"]]
        widths = [0.7 * inch, 5.0 * inch]
    t = Table(data, hAlign="LEFT", colWidths=widths)
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
            props = ", ".join(f"{k}={v}" for k, v in (it.props or {}).items()) if it.props else ""
            rows.append([it.name, str(it.qty or 1), props])
    t = Table(rows, hAlign="LEFT", colWidths=[3.0 * inch, 0.5 * inch, 2.2 * inch])
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


def save_pdf(pc: PlayerCharacter, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(path), pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36
    )
    styles = getSampleStyleSheet()
    title = Paragraph(
        f"<b>{pc.name}</b> — {pc.class_}{f' ({pc.subclass})' if pc.subclass else ''}  L{pc.level}",
        styles["Title"],
    )
    elems = [title, Spacer(1, 0.2 * inch)]
    elems += [Paragraph("<b>Abilities</b>", styles["Heading3"]), _abilities_table(pc), Spacer(1, 0.15 * inch)]
    elems += [
        Paragraph("<b>Proficiencies</b>", styles["Heading3"]),
        _profs_table(pc),
        Spacer(1, 0.15 * inch),
    ]
    elems += [Paragraph("<b>Defense</b>", styles["Heading3"]), _defense_table(pc), Spacer(1, 0.15 * inch)]
    elems += [Paragraph("<b>Spellcasting</b>", styles["Heading3"]), _slots_table(pc), Spacer(1, 0.15 * inch)]
    elems += [Paragraph("<b>Inventory</b>", styles["Heading3"]), _inventory_table(pc)]
    doc.build(elems)

