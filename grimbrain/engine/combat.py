"""Minimal combat round resolution."""
from __future__ import annotations

import random
from typing import Callable, Dict, List, Optional, Any, Tuple
from copy import deepcopy

from .checks import attack_roll, damage_roll, saving_throw
from .dice import roll
from ..models import MonsterSidecar, PC, SpellSidecar, dump_model
from .encounter import compute_encounter

# Imports for the single-attack resolution helper
from ..codex.weapons import Weapon, WeaponIndex
from ..rules.attacks import (
    attack_bonus,
    damage_die,
    damage_modifier,
    choose_attack_ability,
    power_feat_for,
    damage_string,
    has_style,
    has_feat,
)
from ..rules.attack_math import roll_outcome, combine_modes
from .types import Combatant as GBCombatant, Target, Cover, Readied, roll_d20


def _feature_dict(obj) -> Dict[str, Any]:
    feats = getattr(obj, "features", None)
    return feats if isinstance(feats, dict) else {}


def _ability_check(c: GBCombatant, ability: str, *, rng: Optional[random.Random] = None, proficient: bool = False) -> Tuple[int, str]:
    """d20 + ability modifier (+ proficiency if applicable)."""
    rng = rng or random.Random()
    die = roll_d20(rng, pm=c)
    mod = c.actor.ability_mod(ability.upper()) if hasattr(c, "actor") else 0
    prof = c.actor.proficiency_bonus if proficient else 0
    total = die + mod + prof
    note = f"d20({die}) + {ability.upper()}({mod})" + (f" + PROF({c.actor.proficiency_bonus})" if prof else "")
    return total, note


def _skill_proficient(c: GBCombatant, skill: str) -> bool:
    profs = getattr(c, "prof_skills", None)
    if profs:
        skill_lower = skill.lower()
        for entry in profs:
            if str(entry).lower() == skill_lower:
                return True
    if skill.lower() == "athletics" and getattr(c, "proficient_athletics", False):
        return True
    if skill.lower() == "acrobatics" and getattr(c, "proficient_acrobatics", False):
        return True
    return False


def contested_check_grapple_or_shove(attacker: GBCombatant, defender: GBCombatant, *, rng: Optional[random.Random] = None) -> Tuple[bool, str]:
    """Resolve contested Athletics vs Athletics/Acrobatics check."""
    atk_total, atk_note = _ability_check(
        attacker,
        "STR",
        rng=rng,
        proficient=_skill_proficient(attacker, "Athletics"),
    )
    d_str, note_str = _ability_check(
        defender,
        "STR",
        rng=rng,
        proficient=_skill_proficient(defender, "Athletics"),
    )
    d_dex, note_dex = _ability_check(
        defender,
        "DEX",
        rng=rng,
        proficient=_skill_proficient(defender, "Acrobatics"),
    )
    if d_dex >= d_str:
        d_tot, d_note, d_choice = d_dex, note_dex, "DEX(Acrobatics)"
    else:
        d_tot, d_note, d_choice = d_str, note_str, "STR(Athletics)"
    log = (
        f"Grapple/Shove contest: {attacker.name} [{atk_note}] = {atk_total} vs "
        f"{defender.name} [{d_choice} {d_note}] = {d_tot}"
    )
    return atk_total > d_tot, log


def grapple_action(attacker: GBCombatant, defender: GBCombatant, *, rng: Optional[random.Random] = None, notes: Optional[List[str]] = None) -> bool:
    win, log = contested_check_grapple_or_shove(attacker, defender, rng=rng)
    if notes is not None:
        notes.append(log)
    if win and "grappled" not in defender.conditions:
        defender.conditions.add("grappled")
        defender.grappled_by = attacker.name
        if notes is not None:
            notes.append(f"{attacker.name} grapples {defender.name}: speed set to 0.")
        return True
    if notes is not None:
        notes.append("Grapple failed.")
    return False


def escape_grapple_action(defender: GBCombatant, all_combatants: Dict[str, GBCombatant], *, rng: Optional[random.Random] = None, notes: Optional[List[str]] = None) -> bool:
    if "grappled" not in defender.conditions or not defender.grappled_by:
        if notes is not None:
            notes.append("Not grappled → no escape needed.")
        return True
    grappler = all_combatants.get(defender.grappled_by)
    if grappler is None:
        defender.clear_grapple()
        if notes is not None:
            notes.append("Grappler missing → cleared grapple.")
        return True
    win, log = contested_check_grapple_or_shove(defender, grappler, rng=rng)
    if notes is not None:
        notes.append(f"Escape contest: {log}")
    if win:
        defender.clear_grapple()
        if notes is not None:
            notes.append(f"{defender.name} escapes the grapple.")
        return True
    if notes is not None:
        notes.append(f"{defender.name} fails to escape.")
    return False


def shove_action(attacker: GBCombatant, defender: GBCombatant, *, choice: str = "prone", rng: Optional[random.Random] = None,
                 distance_ft: int = 5, reach_threshold: int = 5, notes: Optional[List[str]] = None, trigger_oa_fn=None) -> bool:
    win, log = contested_check_grapple_or_shove(attacker, defender, rng=rng)
    if notes is not None:
        notes.append(log)
    if not win:
        if notes is not None:
            notes.append("Shove failed.")
        return False
    if choice == "prone":
        defender.conditions.add("prone")
        if notes is not None:
            notes.append(f"{attacker.name} shoves {defender.name} prone.")
        return True
    new_distance = distance_ft + 5
    if notes is not None:
        notes.append(f"{attacker.name} pushes {defender.name} 5 ft ({distance_ft}→{new_distance}).")
    if distance_ft <= reach_threshold and new_distance > reach_threshold and callable(trigger_oa_fn):
        if notes is not None:
            notes.append("Push leaves reach → provoking OA.")
        trigger_oa_fn(attacker, defender)
    return True


# ---- PR40 core actions -----------------------------------------------------

def take_dodge_action(actor: GBCombatant, *, notes: Optional[List[str]] = None) -> None:
    """Set the dodging flag on ``actor``."""
    actor.dodging = True
    if notes is not None:
        notes.append(f"{actor.name} takes the Dodge action.")


def take_help_action(helper: GBCombatant, ally: GBCombatant, target: GBCombatant,
                      *, notes: Optional[List[str]] = None) -> None:
    """Grant ``ally`` one advantaged attack against ``target``."""
    ally.help_tokens[target.id] = ally.help_tokens.get(target.id, 0) + 1
    if notes is not None:
        notes.append(
            f"{helper.name} helps {ally.name} against {target.name} (next attack advantage)."
        )


def take_ready_action(actor: GBCombatant, trigger: str, target_id: str,
                      weapon_name: Optional[str] = None, *, notes: Optional[List[str]] = None) -> None:
    actor.readied_action = Readied(trigger=trigger, target_id=target_id, weapon_name=weapon_name)
    if notes is not None:
        notes.append(
            f"{actor.name} readies an attack: trigger={trigger} vs target={target_id}."
        )
class Combatant:
    """Internal mutable combatant state."""

    def __init__(
        self,
        name: str,
        ac: int,
        hp: int,
        attacks: List[Dict[str, object]],
        side: str,
        dex_mod: int = 0,
        con_mod: int = 0,
        max_hp: int | None = None,
        spell_slots: Dict[int, int] | None = None,
    ):
        self.name = name
        self.ac = ac
        self.hp = hp
        self.attacks = attacks
        self.side = side
        self.dex_mod = dex_mod
        self.con_mod = con_mod
        self.max_hp = max_hp if max_hp is not None else hp
        self.spell_slots = spell_slots or {}
        self.defeated = False
        # 5e dying rules
        self.downed = False
        self.stable = False
        self.death_successes = 0
        self.death_failures = 0
        self.concentrating: str | None = None

    def to_state(self) -> Dict[str, object]:
        return {"name": self.name, "hp": self.hp, "defeated": self.defeated}


def _parse_monster(mon: MonsterSidecar, rng: random.Random) -> Combatant:
    ac = int(mon.ac.split()[0])
    hp_str = mon.hp
    if "(" in hp_str and ")" in hp_str:
        expr = hp_str.split("(")[1].split(")")[0]
        seed = rng.randint(0, 10_000_000)
        hp = roll(expr, seed=seed)["total"]
    else:
        hp = int(hp_str.split()[0])
    dex_mod = (mon.dex - 10) // 2
    con_mod = (mon.con - 10) // 2
    attacks: List[Dict[str, object]] = []
    for a in mon.actions_struct:
        attacks.append({"to_hit": a.attack_bonus, "damage_dice": a.damage_dice, "type": a.type})
    return Combatant(mon.name, ac, hp, attacks, "monsters", dex_mod, con_mod, max_hp=hp)


def _parse_pc(pc: PC) -> Combatant:
    attacks = [dump_model(a) for a in pc.attacks]
    return Combatant(
        pc.name,
        pc.ac,
        pc.hp,
        attacks,
        "party",
        0,
        pc.con_mod,
        max_hp=pc.max_hp,
        spell_slots=pc.spell_slots.copy(),
    )


def choose_target(actor: Combatant, enemies: List[Combatant], strategy: str = "lowest_hp", seed: int | None = None) -> Combatant | None:
    """Pick a target from ``enemies`` according to ``strategy``."""
    if not enemies:
        return None
    if strategy == "lowest_hp":
        return min(enemies, key=lambda e: e.hp)
    if strategy == "closest":
        return enemies[0]
    if strategy == "random":
        rng = random.Random(seed)
        return rng.choice(enemies)
    raise ValueError(f"unknown strategy {strategy}")


def run_round(party: List[PC], monsters: List[MonsterSidecar], seed: int | None = None) -> Dict[str, object]:
    """Resolve a single combat round.

    Returns a mapping with ``log`` (list of strings) and ``state`` containing
    updated hit points and defeat flags for all combatants.
    """
    rng = random.Random(seed)
    combatants: List[Combatant] = [_parse_pc(p) for p in party] + [
        _parse_monster(m, rng) for m in monsters
    ]

    # initiative
    for c in combatants:
        init_seed = rng.randint(0, 10_000_000)
        c.init = roll(f"1d20+{c.dex_mod}", seed=init_seed)["total"]
    combatants.sort(key=lambda c: c.init, reverse=True)

    log: List[str] = []

    for actor in combatants:
        if actor.defeated:
            continue
        enemies = [c for c in combatants if c.side != actor.side and not c.defeated]
        if not enemies:
            break
        target_seed = rng.randint(0, 10_000_000)
        target = choose_target(actor, enemies, seed=target_seed)
        if target is None:
            continue
        attack = actor.attacks[0]
        hit_seed = rng.randint(0, 10_000_000)
        atk = attack_roll(attack["to_hit"], target.ac, hit_seed)
        if atk["hit"]:
            dmg_seed = rng.randint(0, 10_000_000)
            dmg = damage_roll(attack["damage_dice"], dmg_seed)
            target.hp -= dmg["total"]
            log.append(f"{actor.name} hits {target.name} for {dmg['total']}")
            if target.hp <= 0:
                target.defeated = True
                log.append(f"{target.name} is defeated")
        else:
            log.append(f"{actor.name} misses {target.name}")

    state = {
        "party": [c.to_state() for c in combatants if c.side == "party"],
        "monsters": [c.to_state() for c in combatants if c.side == "monsters"],
    }
    return {"log": log, "state": state}


def run_encounter(
    party: List[PC],
    monsters: List[MonsterSidecar],
    seed: int | None = None,
    max_rounds: int = 10,
) -> Dict[str, object]:
    """Run combat until one side is defeated or ``max_rounds`` reached."""
    rng = random.Random(seed)
    combatants: List[Combatant] = [_parse_pc(p) for p in party] + [
        _parse_monster(m, rng) for m in monsters
    ]

    # initiative once
    for c in combatants:
        init_seed = rng.randint(0, 10_000_000)
        c.init = roll(f"1d20+{c.dex_mod}", seed=init_seed)["total"]
        c.concentrating = None
    combatants.sort(key=lambda c: c.init, reverse=True)

    log: List[str] = []
    rounds = 0

    party_alive = any(c.side == "party" and not c.defeated for c in combatants)
    monsters_alive = any(c.side == "monsters" and not c.defeated for c in combatants)

    while rounds < max_rounds and party_alive and monsters_alive:
        rounds += 1
        for actor in combatants:
            if actor.defeated:
                continue
            enemies = [c for c in combatants if c.side != actor.side and not c.defeated]
            if not enemies:
                break
            attack = actor.attacks[0]
            level = attack.get("level")
            if level is None and attack.get("spell"):
                level = attack["spell"].get("level")
            if attack.get("type") == "spell" and level:
                slots = actor.spell_slots.get(level, 0)
                if slots <= 0:
                    log.append(
                        f"{actor.name} has no level {level} slots for {attack['name']}"
                    )
                    continue
                actor.spell_slots[level] = slots - 1
            if attack.get("save_dc"):
                dmg_seed = rng.randint(0, 10_000_000)
                dmg_total = damage_roll(attack["damage_dice"], dmg_seed)["total"]
                ability = attack.get("save_ability", "dex")
                for target in enemies:
                    save_seed = rng.randint(0, 10_000_000)
                    mod = getattr(target, f"{ability}_mod", 0)
                    save = saving_throw(attack["save_dc"], mod, seed=save_seed)
                    taken = dmg_total if not save["success"] else dmg_total // 2
                    target.hp -= taken
                    log.append(
                        f"{actor.name}'s {attack['name']} hits {target.name} for {taken}"
                    )
                    if target.hp <= 0:
                        target.defeated = True
                        log.append(f"{target.name} is defeated")
                    if target.concentrating and taken > 0:
                        dc = max(10, taken // 2)
                        con_seed = rng.randint(0, 10_000_000)
                        con_save = saving_throw(dc, target.con_mod, seed=con_seed)
                        if not con_save["success"]:
                            log.append(
                                f"{target.name} loses concentration on {target.concentrating}"
                            )
                            target.concentrating = None
                if attack.get("concentration"):
                    if actor.concentrating:
                        log.append(
                            f"{actor.name} stops concentrating on {actor.concentrating}"
                        )
                    actor.concentrating = attack["name"]
            else:
                enemies_alive = [c for c in enemies if not c.defeated]
                if not enemies_alive:
                    break
                target_seed = rng.randint(0, 10_000_000)
                target = choose_target(actor, enemies_alive, seed=target_seed)
                if target is None:
                    continue
                hit_seed = rng.randint(0, 10_000_000)
                atk = attack_roll(attack.get("to_hit", 0), target.ac, hit_seed)
                if atk["hit"]:
                    dmg_seed = rng.randint(0, 10_000_000)
                    dmg = damage_roll(attack["damage_dice"], dmg_seed)
                    target.hp -= dmg["total"]
                    log.append(
                        f"{actor.name} hits {target.name} for {dmg['total']}"
                    )
                    if target.hp <= 0:
                        target.defeated = True
                        log.append(f"{target.name} is defeated")
                    if target.concentrating and dmg["total"] > 0:
                        dc = max(10, dmg["total"] // 2)
                        con_seed = rng.randint(0, 10_000_000)
                        con_save = saving_throw(dc, target.con_mod, seed=con_seed)
                        if not con_save["success"]:
                            log.append(
                                f"{target.name} loses concentration on {target.concentrating}"
                            )
                            target.concentrating = None
                else:
                    log.append(f"{actor.name} misses {target.name}")
                if attack.get("concentration"):
                    if actor.concentrating:
                        log.append(
                            f"{actor.name} stops concentrating on {actor.concentrating}"
                        )
                    actor.concentrating = attack["name"]
        party_alive = any(
            c.side == "party" and not c.defeated for c in combatants
        )
        monsters_alive = any(
            c.side == "monsters" and not c.defeated for c in combatants
        )
        if not party_alive or not monsters_alive:
            break

    winner = (
        "party" if party_alive and not monsters_alive else "monsters" if monsters_alive and not party_alive else "none"
    )

    state = {
        "party": [c.to_state() for c in combatants if c.side == "party"],
        "monsters": [c.to_state() for c in combatants if c.side == "monsters"],
    }

    xp = compute_encounter(monsters)
    summary = {"winner": winner, "rounds": rounds, "xp": xp["total_xp"], "drops": []}
    return {"log": log, "state": state, "rounds": rounds, "winner": winner, "summary": summary}


def parse_monster_spec(spec: str, lookup: Callable[[str], MonsterSidecar]) -> List[MonsterSidecar]:
    """Expand ``spec`` like ``'goblin x3, goblin boss'`` into sidecars."""
    monsters: List[MonsterSidecar] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        count = 1
        if "x" in part:
            name_part, mult = part.rsplit("x", 1)
            try:
                count = int(mult.strip())
                part = name_part.strip()
            except ValueError:
                part = part
        base = lookup(part)
        for _ in range(count):
            monsters.append(deepcopy(base))
    return monsters


# ---------------------------------------------------------------------------
# Single attack resolution helpers
# ---------------------------------------------------------------------------


def _roll_d20(rng: random.Random, actor=None, *, notes: Optional[List[str]] = None) -> int:
    """Roll a single d20 using ``rng``, applying Lucky if available."""

    log: List[str] = []
    result = roll_d20(rng, pm=actor, log=log)
    if notes is not None:
        notes.extend(log)
    return result


def _parse_die(die: str) -> Tuple[int, int] | None:
    """Parse a dice expression like ``"1d8"`` into ``(1, 8)``.

    Pure integers (``"1"``) and em dashes are handled by the caller and
    return ``None`` here.
    """
    if "d" not in die:
        return None
    n, f = die.lower().split("d", 1)
    return (int(n.strip()), int(f.strip()))


def _roll_damage(die: str, mod: int, *, crit: bool, rng: random.Random) -> Dict[str, Any]:
    """Roll damage dice and apply modifiers.

    ``die`` may be an ``XdY`` expression, a pure integer, or an em dash.
    When ``crit`` is True the dice portion is doubled.
    """
    if die in {"—", "-"}:
        return {"rolls": [], "sum_dice": 0, "mod": 0, "total": 0}
    if die.isdigit():
        base = int(die)
        total = base + mod
        return {"rolls": [base], "sum_dice": base, "mod": mod, "total": total}
    parsed = _parse_die(die)
    assert parsed, f"Bad die string: {die}"
    n, f = parsed
    n = n * 2 if crit else n
    rolls = [rng.randint(1, f) for _ in range(n)]
    s = sum(rolls)
    return {"rolls": rolls, "sum_dice": s, "mod": mod, "total": s + mod}


_COVER_TO_AC = {"none": 0, "half": 2, "three-quarters": 5, "total": 10**9}


def _weapon_has_ranged_profile(w: Weapon) -> bool:
    return w.kind == "ranged" or w.has_prop("thrown") or w.has_prop("range")


def _range_tuple(w: Weapon) -> Tuple[Optional[int], Optional[int]]:
    t = w.range_tuple()
    return (t[0], t[1]) if t else (None, None)


def _long_range_applies(w: Weapon, dist: Optional[int]) -> bool:
    if dist is None or not _weapon_has_ranged_profile(w):
        return False
    n, L = _range_tuple(w)
    return bool(n and L and (n < dist <= L))


def _out_of_range(w: Weapon, dist: Optional[int]) -> bool:
    if dist is None or not _weapon_has_ranged_profile(w):
        return False
    _, L = _range_tuple(w)
    return bool(L and dist > L)


def _ranged_in_melee_disadvantage(w: Weapon, dist: Optional[int]) -> bool:
    # Disadvantage when making a RANGED weapon attack within 5 ft of a hostile creature.
    # Thrown melee (kind="melee" with "thrown") is NOT a ranged weapon, so it's excluded.
    return w.kind == "ranged" and (dist is not None) and dist <= 5


def _effective_ac(ac: int, cover: Cover, has_sharp: bool) -> int:
    if cover == "total":
        return 10**9
    bump = 0 if (has_sharp and cover in {"half", "three-quarters"}) else _COVER_TO_AC.get(cover, 0)
    return ac + bump


def _has(cond: str, cbt) -> bool:
    return cond in getattr(cbt, "conditions", set())


def resolve_attack(
    attacker,
    weapon_name: str,
    target: Target,
    weapon_index: WeaponIndex,
    *,
    base_mode: str = "none",  # "none" | "advantage" | "disadvantage"
    power: bool = False,  # SS/GWM power attack toggle
    offhand: bool = False,
    two_handed: bool = False,
    has_fired_loading_weapon_this_turn: bool = False,
    rng: Optional[random.Random] = None,
    forced_d20: Tuple[int, int] | None = None,  # (d1, d2) for tests
    attacker_state: GBCombatant | None = None,
    defender_state: GBCombatant | None = None,
) -> Dict[str, Any]:
    """Resolve a single weapon attack.

    Returns a dictionary with roll breakdown and outcome. The attacker's
    ammo is reduced when appropriate, but no other character state is
    mutated.
    """

    rng = rng or random.Random()
    w = weapon_index.get(weapon_name)
    notes: List[str] = []
    reach = 10 if w.has_prop("reach") else 5

    # --- PR40: short-lived tactical modifiers ---
    mode = base_mode
    if attacker_state is not None and defender_state is not None:
        if attacker_state.help_tokens.get(defender_state.id, 0) > 0:
            mode = combine_modes(mode, "advantage")
            notes.append("helped attack")
        if defender_state.dodging:
            mode = combine_modes(mode, "disadvantage")
            notes.append("defender dodging")

    light_level = "normal"
    if attacker_state is not None:
        light_level = getattr(attacker_state, "environment_light", light_level)
    else:
        light_level = getattr(attacker, "environment_light", light_level)
    if light_level == "dark":
        feats = _feature_dict(attacker_state) or _feature_dict(attacker)
        try:
            darkvision_range = int(feats.get("darkvision", 0))
        except (TypeError, ValueError):
            darkvision_range = 0
        if darkvision_range < 60:
            mode = combine_modes(mode, "disadvantage")
            notes.append("darkness (no darkvision)")

    # Loading gate
    if w.has_prop("loading") and has_fired_loading_weapon_this_turn:
        return {
            "ok": False,
            "reason": "loading (already fired this turn)",
            "notes": ["loading"],
            "spent_ammo": False,
        }

    # Range/cover adjustments
    has_ss = has_feat(attacker, "Sharpshooter")
    dist = target.distance_ft
    if _out_of_range(w, dist):
        return {
            "ok": False,
            "reason": "out of range",
            "notes": ["out of range"],
            "spent_ammo": False,
        }

    if _long_range_applies(w, dist):
        if has_ss:
            notes.append("long range (Sharpshooter: no disadvantage)")
        else:
            mode = combine_modes(mode, "disadvantage")
            notes.append("long range (disadvantage)")

    eff_ac = _effective_ac(target.ac, target.cover, has_ss)
    if eff_ac >= 10**9:
        return {
            "ok": False,
            "reason": "total cover",
            "notes": ["total cover"],
            "spent_ammo": False,
        }

    # Close-quarters ranged attacks impose disadvantage
    if _ranged_in_melee_disadvantage(w, dist):
        mode = combine_modes(mode, "disadvantage")
        notes.append("in melee with ranged weapon (disadvantage)")

    if _has("prone", target):
        if w.kind == "melee" and dist is not None and dist <= reach:
            mode = combine_modes(mode, "advantage")
            notes.append("prone target (advantage)")
        else:
            mode = combine_modes(mode, "disadvantage")
            notes.append("prone target (disadvantage)")

    if _has("prone", attacker):
        if not (w.kind == "melee" and dist is not None and dist <= reach):
            mode = combine_modes(mode, "disadvantage")
            notes.append("attacker prone (disadvantage)")

    if _has("poisoned", attacker):
        mode = combine_modes(mode, "disadvantage")
        notes.append("poisoned (disadvantage)")

    if _has("restrained", target):
        mode = combine_modes(mode, "advantage")
        notes.append("target restrained (advantage)")

    if _has("restrained", attacker):
        mode = combine_modes(mode, "disadvantage")
        notes.append("restrained (disadvantage)")

    # Attack bonus and d20 roll
    ab = attack_bonus(attacker, w, power=power)

    roller = attacker_state if attacker_state is not None else attacker
    if forced_d20:
        candidates = forced_d20
    else:
        d1 = _roll_d20(rng, roller, notes=notes)
        d2 = _roll_d20(rng, roller, notes=notes)
        candidates = (d1, d2)

    if mode == "advantage":
        d = max(candidates)
    elif mode == "disadvantage":
        d = min(candidates)
    else:
        d = candidates[0]

    is_hit, is_crit = roll_outcome(d, ab, eff_ac)

    if is_hit and w.name.lower() == "net":
        getattr(target, "conditions", set()).add("restrained")
        notes.append("net hit: target restrained (dc 10 str to escape)")

    # Ammo spend (only if we attempted a legal attack; spend regardless of hit)
    spent_ammo = False
    ammo_type = w.ammo_type()
    if ammo_type:
        have = attacker.ammo_count(ammo_type) if hasattr(attacker, "ammo_count") else 0
        if have <= 0:
            return {
                "ok": False,
                "reason": f"no {ammo_type}",
                "notes": [f"out of {ammo_type}"],
                "spent_ammo": False,
            }
        if hasattr(attacker, "spend_ammo"):
            spent_ammo = attacker.spend_ammo(ammo_type, 1)

    # Damage roll
    dmg_die = damage_die(attacker, w, two_handed=two_handed)
    dmg_mod = damage_modifier(
        attacker, w, two_handed=two_handed, offhand=offhand, power=power
    )
    dmg_roll = (
        _roll_damage(dmg_die, dmg_mod, crit=is_crit, rng=rng)
        if is_hit
        else {"rolls": [], "sum_dice": 0, "mod": 0, "total": 0}
    )
    # consume help token if present
    if attacker_state is not None and defender_state is not None:
        attacker_state.consume_help_token(defender_state.id)

    return {
        "ok": True,
        "weapon": w.name,
        "attack_bonus": ab,
        "mode": mode,
        "candidates": candidates,
        "d20": d,
        "is_hit": is_hit,
        "is_crit": is_crit,
        "effective_ac": eff_ac,
        "damage_string": damage_string(
            attacker, w, two_handed=two_handed, offhand=offhand, power=power
        ),
        "damage": dmg_roll,
        "spent_ammo": spent_ammo,
        "notes": notes,
    }


