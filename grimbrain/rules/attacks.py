from typing import List
from ..codex.weapons import Weapon

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


def choose_attack_ability(character, weapon: Weapon) -> str:
    # Ranged weapons use DEX
    if weapon.kind == "ranged":
        return "DEX"
    # Thrown uses STR unless finesse also present
    if weapon.has_prop("thrown") and weapon.has_prop("finesse"):
        return "DEX" if character.ability_mod("DEX") >= character.ability_mod("STR") else "STR"
    if weapon.has_prop("thrown"):
        return "STR"
    # Melee: STR unless finesse; pick higher if finesse
    if weapon.has_prop("finesse"):
        return "DEX" if character.ability_mod("DEX") >= character.ability_mod("STR") else "STR"
    return "STR"


def is_proficient(character, weapon: Weapon) -> bool:
    profs = {p.lower() for p in getattr(character, "proficiencies", getattr(character, "weapon_proficiencies", set()))}
    return (
        f"{weapon.category} weapons" in profs or
        weapon.name.lower() in profs
    )


def attack_bonus(character, weapon: Weapon) -> int:
    ability = choose_attack_ability(character, weapon)
    bonus = character.ability_mod(ability)
    if is_proficient(character, weapon):
        bonus += _pb(character)
    return bonus


def damage_die(character, weapon: Weapon, *, two_handed: bool=False) -> str:
    die = weapon.damage
    v = weapon.versatile_die()
    if v and two_handed:
        die = v
    return die


def damage_modifier(character, weapon: Weapon, *, two_handed: bool=False) -> int:
    ability = choose_attack_ability(character, weapon)
    return character.ability_mod(ability)


def damage_string(character, weapon: Weapon, *, two_handed: bool=False) -> str:
    die = damage_die(character, weapon, two_handed=two_handed)
    mod = damage_modifier(character, weapon, two_handed=two_handed)
    mod_str = format_mod(mod) if mod != 0 else ""
    return f"{die}{(' ' + mod_str) if mod_str else ''} {weapon.damage_type}"


def build_attacks_block(character, weapon_index) -> List[dict]:
    out = []
    for name in getattr(character, "equipped_weapons", []):
        w = weapon_index.get(name)
        ab = attack_bonus(character, w)
        dmg = damage_string(character, w, two_handed=False)
        props = ", ".join(w.properties) if w.properties else ""
        out.append({
            "name": w.name,
            "attack_bonus": ab,
            "damage": dmg,
            "properties": props
        })
    return out
