from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as pkg_version
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from grimbrain.models.pc import ABILITY_ORDER, PlayerCharacter

ABIL_NAMES = {
    "str": "STR",
    "dex": "DEX",
    "con": "CON",
    "int": "INT",
    "wis": "WIS",
    "cha": "CHA",
}


def _caps_csv(items: Iterable[str]) -> str:
    return ", ".join(s.upper() for s in sorted(items)) if items else "—"


def _pkg_version() -> str:
    try:
        return pkg_version("grimbrain")
    except PackageNotFoundError:  # pragma: no cover - local checkout
        return "0.0"


def ability_block(pc: PlayerCharacter) -> Table:
    t = Table(box=None, show_header=False, expand=False)
    for a in ABILITY_ORDER:
        score = getattr(pc.abilities, a)
        mod = pc.ability_mod(a)
        t.add_row(f"[bold]{ABIL_NAMES[a]}[/]", f"{score:>2} ({mod:+d})")
    return t


def prof_block(pc: PlayerCharacter) -> Table:
    t = Table(box=None, show_header=False, expand=False)
    t.add_row("Prof.", f"+{pc.prof}")
    t.add_row("Saves", _caps_csv(pc.save_proficiencies))
    t.add_row("Skills", _caps_csv(pc.skill_proficiencies))
    return t


def defense_block(pc: PlayerCharacter) -> Table:
    t = Table(box=None, show_header=False, expand=False)
    t.add_row("AC", str(pc.ac))
    t.add_row("HP", f"{pc.current_hp}/{pc.max_hp}")
    t.add_row("Init.", f"{pc.initiative:+d}")
    t.add_row("Passive Perception", str(pc.passive_perception))
    return t


def slots_list(pc: PlayerCharacter, show_zero: bool) -> list[str]:
    if not pc.spell_slots:
        return []
    out: list[str] = []
    for i in range(1, 10):
        v = getattr(pc.spell_slots, f"l{i}")
        if v or show_zero:
            out.append(f"L{i}:{v}")
    return out


def slots_block(pc: PlayerCharacter, show_zero: bool) -> Table:
    t = Table(box=None, show_header=False, expand=False)
    parts = slots_list(pc, show_zero)
    t.add_row("Slots", ", ".join(parts) if parts else "—")
    return t


def inventory_block(pc: PlayerCharacter) -> Table:
    t = Table(box=None, show_header=True, expand=False)
    t.add_column("Item")
    t.add_column("Qty")
    t.add_column("Props")
    if not pc.inventory:
        t.add_row("—", "—", "—")
        return t
    for it in pc.inventory:
        t.add_row(
            it.name,
            str(it.qty or 1),
            (
                ", ".join(f"{k}={v}" for k, v in (it.props or {}).items())
                if it.props
                else ""
            ),
        )
    return t


def render_console(
    pc: PlayerCharacter,
    meta: dict[str, str] | None = None,
    show_zero_slots: bool = False,
) -> None:
    c = Console()
    header = f"[bold]{pc.name}[/] — {pc.class_}{f' ({pc.subclass})' if pc.subclass else ''}  L{pc.level}"
    c.rule(header)
    c.print(Panel(ability_block(pc), title="Abilities", border_style="cyan"))
    c.print(Panel(prof_block(pc), title="Proficiencies", border_style="magenta"))
    c.print(Panel(defense_block(pc), title="Defense", border_style="green"))
    c.print(
        Panel(
            slots_block(pc, show_zero_slots),
            title="Spellcasting",
            border_style="yellow",
        )
    )
    c.print(Panel(inventory_block(pc), title="Inventory", border_style="blue"))
    if meta:
        meta_line = "  •  ".join(f"{k}: {v}" for k, v in meta.items())
        c.rule(f"[dim]{meta_line}[/dim]")


MD_HEADER = (
    "# {name}\n\n"
    "**Class:** {klass}{sub}  \n"
    "**Level:** {level}  \n"
    "**AC:** {ac}  \n"
    "**HP:** {hp}\n\n"
)


def to_markdown(
    pc: PlayerCharacter,
    meta: dict[str, str] | None = None,
    show_zero_slots: bool = False,
) -> str:
    sub = f" ({pc.subclass})" if pc.subclass else ""
    out = MD_HEADER.format(
        name=pc.name,
        klass=pc.class_,
        sub=sub,
        level=pc.level,
        ac=pc.ac,
        hp=f"{pc.current_hp}/{pc.max_hp}",
    )
    out += "## Abilities\n\n"
    for a in ABILITY_ORDER:
        score = getattr(pc.abilities, a)
        mod = pc.ability_mod(a)
        out += f"- **{ABIL_NAMES[a]}**: {score} ({mod:+d})\n"
    out += "\n## Proficiencies\n\n"
    out += (
        f"- **Proficiency Bonus**: +{pc.prof}\n"
        f"- **Saving Throws**: {_caps_csv(pc.save_proficiencies)}\n"
        f"- **Skills**: {_caps_csv(pc.skill_proficiencies)}\n\n"
    )
    out += "## Derived\n\n"
    out += (
        f"- **Initiative**: {pc.initiative:+d}\n"
        f"- **Passive Perception**: {pc.passive_perception}\n\n"
    )
    out += "## Spellcasting\n\n"
    parts = slots_list(pc, show_zero_slots)
    out += f"- **Slots**: {', '.join(parts) if parts else '—'}\n\n"
    out += "## Inventory\n\n"
    if not pc.inventory:
        out += "- —\n"
    else:
        for it in pc.inventory:
            props = (
                ", ".join(f"{k}={v}" for k, v in (it.props or {}).items())
                if it.props
                else ""
            )
            out += f"- {it.name} x{it.qty or 1} {props}\n"
    meta = meta or {}
    meta.setdefault("version", _pkg_version())
    meta.setdefault("generated", datetime.utcnow().isoformat() + "Z")
    footer = "  •  ".join(f"{k.upper()}: {v}" for k, v in meta.items())
    out += f"\n---\n\n{footer}\n"
    return out


def save_markdown(
    pc: PlayerCharacter,
    path: Path,
    meta: dict[str, str] | None = None,
    show_zero_slots: bool = False,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        to_markdown(pc, meta=meta, show_zero_slots=show_zero_slots),
        encoding="utf-8",
    )
