from __future__ import annotations

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
    t.add_row("Saves", ", ".join(sorted(pc.save_proficiencies)) or "—")
    t.add_row("Skills", ", ".join(sorted(pc.skill_proficiencies)) or "—")
    return t


def defense_block(pc: PlayerCharacter) -> Table:
    t = Table(box=None, show_header=False, expand=False)
    t.add_row("AC", str(pc.ac))
    t.add_row("HP", f"{pc.current_hp}/{pc.max_hp}")
    t.add_row("Init.", f"{pc.initiative:+d}")
    t.add_row("Passive Perception", str(pc.passive_perception))
    return t


def slots_block(pc: PlayerCharacter) -> Table:
    t = Table(box=None, show_header=False, expand=False)
    if not pc.spell_slots:
        t.add_row("Slots", "—")
        return t
    levels = [f"L{i}" for i in range(1, 10)]
    values = [getattr(pc.spell_slots, f"l{i}") for i in range(1, 10)]
    t.add_row("Slots", ", ".join(f"{lvl}:{v}" for lvl, v in zip(levels, values) if v))
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


def render_console(pc: PlayerCharacter) -> None:
    c = Console()
    header = f"[bold]{pc.name}[/] — {pc.class_}{f' ({pc.subclass})' if pc.subclass else ''}  L{pc.level}"
    c.rule(header)
    c.print(Panel(ability_block(pc), title="Abilities", border_style="cyan"))
    c.print(Panel(prof_block(pc), title="Proficiencies", border_style="magenta"))
    c.print(Panel(defense_block(pc), title="Defense", border_style="green"))
    c.print(Panel(slots_block(pc), title="Spellcasting", border_style="yellow"))
    c.print(Panel(inventory_block(pc), title="Inventory", border_style="blue"))


MD_HEADER = (
    "# {name}\n\n"
    "**Class:** {klass}{sub}  \n"
    "**Level:** {level}  \n"
    "**AC:** {ac}  \n"
    "**HP:** {hp}\n\n"
)


def to_markdown(pc: PlayerCharacter) -> str:
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
    saves = ", ".join(sorted(pc.save_proficiencies)) or "—"
    skills = ", ".join(sorted(pc.skill_proficiencies)) or "—"
    out += (
        f"- **Proficiency Bonus**: +{pc.prof}\n"
        f"- **Saving Throws**: {saves}\n"
        f"- **Skills**: {skills}\n\n"
    )
    out += "## Derived\n\n"
    out += (
        f"- **Initiative**: {pc.initiative:+d}\n"
        f"- **Passive Perception**: {pc.passive_perception}\n\n"
    )
    out += "## Spellcasting\n\n"
    if pc.spell_slots:
        parts = []
        for i in range(1, 10):
            v = getattr(pc.spell_slots, f"l{i}")
            if v:
                parts.append(f"L{i}:{v}")
        out += "- **Slots**: " + (", ".join(parts) if parts else "—") + "\n\n"
    else:
        out += "- **Slots**: —\n\n"
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
    return out


def save_markdown(pc: PlayerCharacter, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(to_markdown(pc), encoding="utf-8")
