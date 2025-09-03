from typing import List
from ..codex.weapons import Weapon
from .attack_math import double_die_text, hit_probabilities, combine_modes
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


_COVER_TO_AC = {"none": 0, "half": 2, "three-quarters": 5, "total": 9999}


def _weapon_has_ranged_profile(w: Weapon) -> bool:
    return w.kind == "ranged" or w.has_prop("thrown") or w.has_prop("range")


def _long_range_applies(w: Weapon, distance_ft: int | None) -> bool:
    if distance_ft is None or not _weapon_has_ranged_profile(w):
        return False
    rng = w.range_tuple()
    if not rng:
        return False
    normal, long = rng
    return normal < distance_ft <= long


def _out_of_range(w: Weapon, distance_ft: int | None) -> bool:
    if distance_ft is None or not _weapon_has_ranged_profile(w):
        return False
    rng = w.range_tuple()
    if not rng:
        return False
    _, long = rng
    return distance_ft > long


def _effective_ac(ac: int, cover: str, has_sharpshooter: bool) -> int:
    if cover == "total":
        return 10 ** 9
    bump = 0 if (has_sharpshooter and cover in {"half", "three-quarters"}) else _COVER_TO_AC.get(cover, 0)
    return ac + bump


def _apply_range_cover_context(character, w: Weapon, *, base_mode: str, target_ac: int | None,
                               target_distance: int | None, cover: str | None):
    eff_mode = base_mode
    eff_ac = target_ac
    notes: list[str] = []

    has_ss = has_feat(character, "Sharpshooter")

    if target_distance is not None and _weapon_has_ranged_profile(w):
        if _out_of_range(w, target_distance):
            return eff_mode, eff_ac, notes + ["out of range"], True
        if _long_range_applies(w, target_distance):
            if not has_ss:
                eff_mode = combine_modes(eff_mode, "disadvantage")
                notes.append("long range (disadvantage)")
            else:
                notes.append("long range (Sharpshooter: no disadvantage)")

    if target_ac is not None and cover:
        eff_ac = _effective_ac(target_ac, cover, has_ss)
        if cover != "none":
            if cover == "total":
                notes.append("total cover")
            else:
                if has_ss:
                    notes.append(f"{cover} (Sharpshooter: ignore cover)")
                else:
                    bump = _COVER_TO_AC[cover]
                    notes.append(f"{cover} (+{bump} AC)")

    return eff_mode, eff_ac, notes, False


def has_style(character, style_name: str) -> bool:
    return style_name in getattr(character, "fighting_styles", set())


def has_feat(character, feat_name: str) -> bool:
    return feat_name in getattr(character, "feats", set())


def _ss_eligible(weapon: Weapon) -> bool:
    # Sharpshooter: ranged weapons only (not thrown melee)
    return weapon.kind == "ranged"


def _gwm_eligible(weapon: Weapon) -> bool:
    # Great Weapon Master: heavy melee weapons
    return (weapon.kind == "melee") and ("heavy" in weapon.properties)


def power_feat_for(character, weapon: Weapon) -> str | None:
    if has_feat(character, "Sharpshooter") and _ss_eligible(weapon):
        return "Sharpshooter"
    if has_feat(character, "Great Weapon Master") and _gwm_eligible(weapon):
        return "Great Weapon Master"
    return None


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


def attack_bonus(character, weapon: Weapon, *, power: bool = False) -> int:
    ability = choose_attack_ability(character, weapon)
    bonus = character.ability_mod(ability)
    if is_proficient(character, weapon):
        bonus += _pb(character)
    # Archery applies to ranged WEAPONS (not thrown melee)
    if weapon.kind == "ranged" and has_style(character, "Archery"):
        bonus += 2
    if power and power_feat_for(character, weapon):
        bonus -= 5
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
    power: bool = False,
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
    if power and power_feat_for(character, weapon):
        mod += 10
    return mod


def damage_string(
    character,
    weapon: Weapon,
    *,
    two_handed: bool = False,
    offhand: bool = False,
    power: bool = False,
) -> str:
    die = damage_die(character, weapon, two_handed=two_handed)
    if die in {"—", "-"}:
        return "— special"
    mod = damage_modifier(
        character,
        weapon,
        two_handed=two_handed,
        offhand=offhand,
        power=power,
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
    show_power_variant: bool = True,
    target_distance: int | None = None,
    cover: str | None = None,
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
            eff_mode, eff_ac, notes, oob = _apply_range_cover_context(
                character,
                w,
                base_mode=mode,
                target_ac=target_ac,
                target_distance=target_distance,
                cover=cover or "none",
            )
            if oob or eff_ac >= 10 ** 9:
                odds = f"unattackable [{', '.join(notes)}]" if notes else "unattackable"
            else:
                p = hit_probabilities(ab, eff_ac, eff_mode)
                odds = (
                    f"hit {_fmt_pct(p['hit'])} • crit {_fmt_pct(p['crit'])} vs AC {eff_ac}"
                    + (f" [{', '.join(notes)}]" if notes else "")
                )

        notes = weapon_notes(w)

        entry = {
            "name": w.name,
            "attack_bonus": ab,
            "damage": dmg,
            "properties": properties,
            **({"odds": odds} if odds else {}),
            **({"notes": notes} if notes else {}),
        }
        out.append(entry)

        pf = power_feat_for(character, w)
        if show_power_variant and pf:
            ab_p = attack_bonus(character, w, power=True)
            dmg_p = damage_display(character, w).replace(
                damage_string(character, w, two_handed=False),
                damage_string(character, w, two_handed=False, power=True),
            )
            label = "SS -5/+10" if pf == "Sharpshooter" else "GWM -5/+10"
            e2 = {
                "name": f"{w.name} ({label})",
                "attack_bonus": ab_p,
                "damage": dmg_p,
                "properties": properties,
            }
            if target_ac is not None:
                eff_mode, eff_ac, notes, oob = _apply_range_cover_context(
                    character,
                    w,
                    base_mode=mode,
                    target_ac=target_ac,
                    target_distance=target_distance,
                    cover=cover or "none",
                )
                if oob or eff_ac >= 10 ** 9:
                    e2["odds"] = f"unattackable [{', '.join(notes)}]" if notes else "unattackable"
                else:
                    p2 = hit_probabilities(ab_p, eff_ac, eff_mode)
                    e2["odds"] = (
                        f"hit {_fmt_pct(p2['hit'])} • crit {_fmt_pct(p2['crit'])} vs AC {eff_ac}"
                        + (f" [{', '.join(notes)}]" if notes else "")
                    )
            out.append(e2)

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
                eff_mode, eff_ac, notes, oob = _apply_range_cover_context(
                    character,
                    w,
                    base_mode=mode,
                    target_ac=target_ac,
                    target_distance=target_distance,
                    cover=cover or "none",
                )
                if oob or eff_ac >= 10 ** 9:
                    odds = f"unattackable [{', '.join(notes)}]" if notes else "unattackable"
                else:
                    p = hit_probabilities(ab, eff_ac, eff_mode)
                    odds = (
                        f"hit {_fmt_pct(p['hit'])} • crit {_fmt_pct(p['crit'])} vs AC {eff_ac}"
                        + (f" [{', '.join(notes)}]" if notes else "")
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
