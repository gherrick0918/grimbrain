from typing import List
from ..codex.weapons import Weapon
from .attack_math import double_die_text, hit_probabilities
from .weapon_notes import weapon_notes

# Expect character to expose:
#   ability_mod("STR"/"DEX"), prof or proficiency_bonus, weapon_proficiencies or proficiencies
#   equipped_weapons: list[str]


def _pb(character) -> int:
    pb = getattr(character, "proficiency_bonus", None)
    if pb is None:
        pb = getattr(character, "prof", 0)
    return pb


def format_mod(n: int) -> str:
    return f"+{n}" if n >= 0 else str(n)


def _fmt_pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def has_style(character, style_name: str) -> bool:
    return style_name in getattr(character, "fighting_styles", set())


def choose_attack_ability(character, weapon: Weapon) -> str:
    # Ranged weapons use DEX
    if weapon.kind == "ranged":
        return "DEX"
    # Thrown uses STR unless finesse also present
    if weapon.has_prop("thrown") and weapon.has_prop("finesse"):
        return (
            "DEX"
            if character.ability_mod("DEX") >= character.ability_mod("STR")
            else "STR"
        )
    if weapon.has_prop("thrown"):
        return "STR"
    # Melee: STR unless finesse; pick higher if finesse
    if weapon.has_prop("finesse"):
        return (
            "DEX"
            if character.ability_mod("DEX") >= character.ability_mod("STR")
            else "STR"
        )
    return "STR"


def is_proficient(character, weapon: Weapon) -> bool:
    profs = {
        p.lower()
        for p in getattr(
            character,
            "proficiencies",
            getattr(character, "weapon_proficiencies", set()),
        )
    }
    return f"{weapon.category} weapons" in profs or weapon.name.lower() in profs


def attack_bonus(character, weapon: Weapon) -> int:
    ability = choose_attack_ability(character, weapon)
    bonus = character.ability_mod(ability)
    if is_proficient(character, weapon):
        bonus += _pb(character)
    # Archery applies to ranged WEAPONS (not thrown melee)
    if weapon.kind == "ranged" and has_style(character, "Archery"):
        bonus += 2
    return bonus


def _dueling_applies(character, weapon: Weapon, *, two_handed: bool, offhand: bool) -> bool:
    # Dueling: melee weapon, wielded in one hand, and no other weapons.
    if weapon.kind != "melee":
        return False
    if two_handed or weapon.has_prop("two-handed"):
        return False
    # If we're computing an explicit off-hand strike, Dueling never applies.
    if offhand:
        return False
    # No other weapons equipped in the other hand.
    return getattr(character, "equipped_offhand", None) is None


def damage_die(character, weapon: Weapon, *, two_handed: bool = False) -> str:
    die = weapon.damage
    v = weapon.versatile_die()
    if v and two_handed:
        die = v
    return die


def damage_modifier(
    character,
    weapon: Weapon,
    *,
    two_handed: bool = False,
    offhand: bool = False,
) -> int:
    # Off-hand: no mod unless Two-Weapon Fighting style
    if offhand and not has_style(character, "Two-Weapon Fighting"):
        return 0
    ability = choose_attack_ability(character, weapon)
    mod = character.ability_mod(ability)
    # Dueling: +2 to damage (one-handed melee, no other weapons)
    if (
        _dueling_applies(
            character, weapon, two_handed=two_handed, offhand=offhand
        )
        and has_style(character, "Dueling")
    ):
        mod += 2
    return mod


def damage_string(
    character,
    weapon: Weapon,
    *,
    two_handed: bool = False,
    offhand: bool = False,
) -> str:
    die = damage_die(character, weapon, two_handed=two_handed)
    if die in {"—", "-"}:
        return "— special"
    mod = damage_modifier(
        character, weapon, two_handed=two_handed, offhand=offhand
    )
    mod_str = format_mod(mod) if mod != 0 else ""
    return f"{die}{(' ' + mod_str) if mod_str else ''} {weapon.damage_type}"


# NEW: crit damage string (doubles dice only)
def crit_damage_string(
    character, weapon, *, two_handed: bool = False, offhand: bool = False
) -> str:
    die = damage_die(character, weapon, two_handed=two_handed)
    # If weapon has no dice (e.g., "1" Blowgun) or is "—" Net, leave die as-is / unchanged.
    if die in {"—", "-"}:
        return "— special"
    die_crit = double_die_text(die)
    mod = damage_modifier(
        character, weapon, two_handed=two_handed, offhand=offhand
    )
    mod_str = format_mod(mod) if mod != 0 else ""
    return f"{die_crit}{(' ' + mod_str) if mod_str else ''} {weapon.damage_type}"


def damage_display(character, weapon: Weapon) -> str:
    base = damage_string(character, weapon, two_handed=False)
    v = weapon.versatile_die()
    if not v:
        return base
    two_h = damage_string(character, weapon, two_handed=True)
    if two_h != base:
        return f"{base} ({two_h} two-handed)"
    return base


def can_two_weapon(weapon: Weapon) -> bool:
    return weapon.kind == "melee" and ("light" in weapon.properties)


def build_attacks_block(
    character,
    weapon_index,
    *,
    target_ac: int | None = None,
    mode: str = "none",
) -> List[dict]:
    out = []
    for name in getattr(character, "equipped_weapons", []):
        try:
            w = weapon_index.get(name)
        except KeyError:
            continue
        ab = attack_bonus(character, w)
        dmg = damage_display(character, w)
        props = (
            ", ".join(p.replace("range:", "").replace("/", "/") for p in w.properties)
            if w.properties
            else ""
        )

        ammo_note = ""
        at = w.ammo_type()
        if at:
            count = character.ammo_count(at)
            ammo_note = f"{at}: {count}"

        properties = ", ".join(x for x in [props, ammo_note] if x)

        odds = ""
        if target_ac is not None:
            p = hit_probabilities(ab, target_ac, mode)
            odds = (
                f"hit {_fmt_pct(p['hit'])} • crit {_fmt_pct(p['crit'])} vs AC {target_ac}"
            )

        notes = weapon_notes(w)

        out.append(
            {
                "name": w.name,
                "attack_bonus": ab,
                "damage": dmg,
                "properties": properties,
                **({"odds": odds} if odds else {}),
                **({"notes": notes} if notes else {}),
            }
        )

    off = getattr(character, "equipped_offhand", None)
    if off:
        try:
            w = weapon_index.get(off)
        except KeyError:
            w = None
        if w and can_two_weapon(w):
            ab = attack_bonus(character, w)
            dmg = damage_string(character, w, offhand=True)
            props = (
                ", ".join(p.replace("range:", "").replace("/", "/") for p in w.properties)
                if w.properties
                else ""
            )

            ammo_note = ""
            at = w.ammo_type()
            if at:
                count = character.ammo_count(at)
                ammo_note = f"{at}: {count}"
            properties = ", ".join(x for x in [props, ammo_note] if x)

            odds = ""
            if target_ac is not None:
                p = hit_probabilities(ab, target_ac, mode)
                odds = (
                    f"hit {_fmt_pct(p['hit'])} • crit {_fmt_pct(p['crit'])} vs AC {target_ac}"
                )

            out.append(
                {
                    "name": f"{w.name} (off-hand)",
                    "attack_bonus": ab,
                    "damage": dmg,
                    "properties": properties,
                    **({"odds": odds} if odds else {}),
                }
            )
    return out
