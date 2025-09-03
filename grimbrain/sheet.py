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
from grimbrain.characters import spell_save_dc, spell_attack_bonus
from grimbrain.codex.weapons import WeaponIndex
from grimbrain.codex.armor import ArmorIndex
from grimbrain.rules.attacks import format_mod
from grimbrain.rules.defense import compute_ac

ABIL_NAMES = {
    "str": "STR",
    "dex": "DEX",
    "con": "CON",
    "int": "INT",
    "wis": "WIS",
    "cha": "CHA",
}

BASE_PATH = Path(__file__).resolve().parent.parent
WEAPON_INDEX = WeaponIndex.load(BASE_PATH / "data" / "weapons.json")
ARMOR_INDEX = ArmorIndex.load(BASE_PATH / "data" / "armor.json")


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
        t.add_row(f"[bold]{ABIL_NAMES[a]}[/]", f"{score:>2} ({format_mod(mod)})")
    return t


def prof_block(pc: PlayerCharacter) -> Table:
    t = Table(box=None, show_header=False, expand=False)
    t.add_row("Prof.", format_mod(pc.prof))
    t.add_row("Saves", _caps_csv(pc.save_proficiencies))
    t.add_row("Skills", _caps_csv(pc.skill_proficiencies))
    langs = ", ".join(pc.languages) if pc.languages else "—"
    tools = ", ".join(pc.tool_proficiencies) if pc.tool_proficiencies else "—"
    t.add_row("Languages", langs)
    t.add_row("Tools", tools)
    return t


def defense_block(pc: PlayerCharacter) -> Table:
    t = Table(box=None, show_header=False, expand=False)
    t.add_row("AC", str(pc.ac))
    t.add_row("HP", f"{pc.current_hp}/{pc.max_hp}")
    t.add_row("Init.", format_mod(pc.initiative))
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


def spellcasting_block(pc: PlayerCharacter, show_zero: bool) -> Table:
    t = Table(box=None, show_header=False, expand=False)
    dc = spell_save_dc(pc)
    atk = spell_attack_bonus(pc)
    if dc is not None and atk is not None:
        t.add_row("Spell Save DC", str(dc))
        t.add_row("Spell Attack", format_mod(atk))
    parts = slots_list(pc, show_zero)
    t.add_row("Slots", ", ".join(parts) if parts else "—")
    if pc.prepared_spells:
        t.add_row("Prepared", ", ".join(pc.prepared_spells))
    return t


def attacks_block(
    pc: PlayerCharacter,
    *,
    target_ac: int | None = None,
    mode: str = "none",
) -> Table:
    t = Table(box=None, show_header=True, expand=False)
    t.add_column("Name")
    t.add_column("Atk")
    t.add_column("Damage")
    t.add_column("Props")
    attacks = pc.attacks(WEAPON_INDEX, target_ac=target_ac, mode=mode)
    if not attacks:
        t.add_row("—", "—", "—", "")
        return t
    for a in attacks:
        atk = format_mod(a["attack_bonus"])
        dmg = a["damage"]
        if a.get("odds"):
            dmg += f" [{a['odds']}]"
        t.add_row(a["name"], atk, dmg, a["properties"])
        if a.get("notes"):
            for n in a["notes"]:
                t.add_row(f"  · {n}", "", "", "")
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
    *,
    target_ac: int | None = None,
    mode: str = "none",
) -> None:
    c = Console()
    header = f"[bold]{pc.name}[/] — {pc.class_}{f' ({pc.subclass})' if pc.subclass else ''}  L{pc.level}"
    c.rule(header)
    ac_info = compute_ac(pc, ARMOR_INDEX)
    parts = ", ".join(ac_info["components"])
    notes = "; ".join(ac_info["notes"]) if ac_info["notes"] else ""
    line = f"AC {ac_info['ac']} — {parts}"
    if notes:
        line += f"; {notes}"
    c.print(line)
    c.print(Panel(ability_block(pc), title="Abilities", border_style="cyan"))
    c.print(Panel(prof_block(pc), title="Proficiencies", border_style="magenta"))
    c.print(Panel(defense_block(pc), title="Defense", border_style="green"))
    c.print(
        Panel(
            attacks_block(pc, target_ac=target_ac, mode=mode),
            title="Attacks & Spellcasting",
            border_style="red",
        )
    )
    c.print(
        Panel(
            spellcasting_block(pc, show_zero_slots),
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
    *,
    target_ac: int | None = None,
    mode: str = "none",
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
        out += f"- **{ABIL_NAMES[a]}**: {score} ({format_mod(mod)})\n"
    out += "\n## Proficiencies\n\n"
    out += (
        f"- **Proficiency Bonus**: {format_mod(pc.prof)}\n"
        f"- **Saving Throws**: {_caps_csv(pc.save_proficiencies)}\n"
        f"- **Skills**: {_caps_csv(pc.skill_proficiencies)}\n"
        f"- **Languages**: {', '.join(pc.languages) if pc.languages else '—'}\n"
        f"- **Tools**: {', '.join(pc.tool_proficiencies) if pc.tool_proficiencies else '—'}\n\n"
    )
    out += "## Derived\n\n"
    out += (
        f"- **Initiative**: {format_mod(pc.initiative)}\n"
        f"- **Passive Perception**: {pc.passive_perception}\n\n"
    )
    out += "## Attacks & Spellcasting\n\n"
    attacks = pc.attacks(WEAPON_INDEX, target_ac=target_ac, mode=mode)
    if not attacks:
        out += "- —\n\n"
    else:
        for a in attacks:
            props = f" ({a['properties']})" if a["properties"] else ""
            odds = f" [{a['odds']}]" if a.get("odds") else ""
            out += (
                f"- {a['name']}: {format_mod(a['attack_bonus'])} to hit, {a['damage']}{odds}{props}\n"
            )
            if a.get("notes"):
                for n in a["notes"]:
                    out += f"  · {n}\n"
        out += "\n"
    out += "## Spellcasting\n\n"
    dc = spell_save_dc(pc)
    atk = spell_attack_bonus(pc)
    if dc is not None and atk is not None:
        out += f"- **Spell Save DC**: {dc}\n- **Spell Attack**: {format_mod(atk)}\n"
    parts = slots_list(pc, show_zero_slots)
    out += f"- **Slots**: {', '.join(parts) if parts else '—'}\n"
    if pc.prepared_spells:
        out += f"- **Prepared**: {', '.join(pc.prepared_spells)}\n"
    out += "\n"
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
    *,
    target_ac: int | None = None,
    mode: str = "none",
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        to_markdown(
            pc,
            meta=meta,
            show_zero_slots=show_zero_slots,
            target_ac=target_ac,
            mode=mode,
        ),
        encoding="utf-8",
    )
