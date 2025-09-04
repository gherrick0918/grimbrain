from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import random
from pathlib import Path

from .types import Combatant, Target, Cover
from .death import roll_death_save, apply_damage_while_down
from .damage import apply_defenses
from .concentration import check_concentration_on_damage, drop_concentration
from ..codex.weapons import WeaponIndex
from ..codex.armor import ArmorIndex
from ..rules.defense import compute_ac
from ..rules.attacks import (
    attack_bonus, damage_die, damage_modifier, damage_string, power_feat_for,
    can_two_weapon, has_style, has_feat
)
from ..rules.attack_math import hit_probabilities


# ---------- initiative ----------
def _init_mod(c) -> int:
    # Raw DEX mod; optionally add c.initiative_bonus if you later add it
    return (c.dex_score - 10) // 2


def roll_initiative(a: Combatant, b: Combatant, rng: random.Random) -> Tuple[Combatant, Combatant, Dict[str,int]]:
    dA = rng.randint(1,20); dB = rng.randint(1,20)
    iA = dA + _init_mod(a.actor)
    iB = dB + _init_mod(b.actor)
    if iA > iB or (iA == iB and _init_mod(a.actor) >= _init_mod(b.actor)):
        return a, b, {"A": iA, "B": iB}
    return b, a, {"A": iB, "B": iA}


# ---------- simple DPR chooser for SS/GWM toggle ----------
def _avg_die(die: str) -> float:
    # "XdY" -> X*(Y+1)/2 ; "1" -> 1 ; "—" -> 0
    if die in {"—", "-"}: return 0.0
    if "d" not in die: return float(int(die))
    n, f = die.lower().split("d", 1)
    return int(n) * (int(f)+1) / 2.0


def _expected_damage(actor, weapon, ac: int, *, power: bool, offhand: bool, two_handed: bool) -> float:
    ab = attack_bonus(actor, weapon, power=power)
    p = hit_probabilities(ab, ac, "none")  # runner’s base mode is “none”; range/cover handled in resolve step
    base_die = damage_die(actor, weapon, two_handed=two_handed)
    mod = damage_modifier(actor, weapon, offhand=offhand, two_handed=two_handed, power=power)
    normal = _avg_die(base_die) + mod
    # crit doubles only dice; average extra = _avg_die(base_die) (mod added once)
    return p["normal"] * normal + p["crit"] * (normal + _avg_die(base_die))


def _should_power(actor, weapon, ac: int) -> bool:
    pf = power_feat_for(actor, weapon)
    if not pf:
        return False
    # Compare expected value with and without -5/+10 at the given AC
    e_base = _expected_damage(actor, weapon, ac, power=False, offhand=False, two_handed=False)
    e_pow  = _expected_damage(actor, weapon, ac, power=True,  offhand=False, two_handed=False)
    return e_pow > e_base


# ---------- one turn ----------
def _ac_for(defender: Combatant, armor_idx: ArmorIndex) -> int:
    return int(compute_ac(defender.actor, armor_idx)["ac"])


@dataclass
class TurnResult:
    log: List[str]
    damage: int
    target_down: bool
    used_loading: bool


def _attack_once(attacker: Combatant, defender: Combatant, wname: str, *,
                 weapon_idx: WeaponIndex, armor_idx: ArmorIndex,
                 rng: random.Random, already_loaded_this_turn: bool) -> TurnResult:
    from .combat import resolve_attack  # reuse engine core
    log: List[str] = []
    w = weapon_idx.get(wname)
    ac = _ac_for(defender, armor_idx)

    power = _should_power(attacker.actor, w, ac)
    res = resolve_attack(
        attacker.actor, wname,
        Target(ac=ac, hp=defender.hp, cover=defender.cover, distance_ft=defender.distance_ft),
        weapon_idx,
        base_mode="none", power=power, offhand=False, two_handed=False,
        has_fired_loading_weapon_this_turn=already_loaded_this_turn,
        rng=rng
    )

    if not res["ok"]:
        log.append(f"{attacker.name} cannot attack: {res['reason']} ({', '.join(res.get('notes', []))})")
        return TurnResult(log, 0, False, False)

    tag = "CRIT" if res["is_crit"] else ("HIT" if res["is_hit"] else "MISS")
    odds_note = f" [{', '.join(res['notes'])}]" if res["notes"] else ""
    log.append(f"{attacker.name} attacks with {res['weapon']} vs AC {res['effective_ac']} => {tag}{odds_note}")
    cand = "/".join(map(str, res["candidates"]))
    log.append(f"  d20 {res['d20']} (candidates {cand})  AB {res['attack_bonus']}")
    log.append(f"  damage {res['damage_string']}: rolls={res['damage']['rolls']} total={res['damage']['total']}")
    if res["spent_ammo"]:
        log.append("  ammo: spent 1")

    dtype = w.damage_type
    raw = int(res["damage"]["total"])
    final, notes2, _ = apply_defenses(raw, dtype, defender)
    for n in notes2:
        log.append(f"  {n}")

    return TurnResult(log, final, False, w.has_prop("loading"))


def _offhand_if_applicable(attacker: Combatant, defender: Combatant, *,
                           weapon_idx: WeaponIndex, armor_idx: ArmorIndex,
                           rng: random.Random, already_loaded_this_turn: bool) -> TurnResult:
    log: List[str] = []
    if not attacker.offhand:
        return TurnResult(log, 0, False, False)
    w = weapon_idx.get(attacker.offhand)
    # Only allow melee light weapons (basic SRD TWF) and ensure not loading
    if not can_two_weapon(w) or w.has_prop("loading"):
        return TurnResult(log, 0, False, False)

    from .combat import resolve_attack
    ac = _ac_for(defender, armor_idx)
    res = resolve_attack(
        attacker.actor, attacker.offhand,
        Target(ac=ac, hp=defender.hp, cover=defender.cover, distance_ft=defender.distance_ft),
        weapon_idx,
        base_mode="none", power=False, offhand=True, two_handed=False,
        has_fired_loading_weapon_this_turn=already_loaded_this_turn,
        rng=rng
    )
    if not res["ok"]:
        return TurnResult(log, 0, False, False)
    tag = "CRIT" if res["is_crit"] else ("HIT" if res["is_hit"] else "MISS")
    log.append(f"  Off-hand {res['weapon']} => {tag}")
    log.append(f"    damage {res['damage_string']}: rolls={res['damage']['rolls']} total={res['damage']['total']}")
    dtype = w.damage_type
    raw = int(res["damage"]["total"])
    final, notes2, _ = apply_defenses(raw, dtype, defender)
    for n in notes2:
        log.append(f"    {n}")
    return TurnResult(log, final, False, False)


def take_turn(attacker: Combatant, defender: Combatant, *,
              weapon_idx: WeaponIndex, armor_idx: ArmorIndex,
              rng: random.Random) -> List[str]:
    log: List[str] = []
    # Track per-turn loading usage
    used_loading = False

    # Start-of-turn death save if attacker is down
    if attacker.hp <= 0 and not attacker.death.stable and not attacker.death.dead:
        outcome = roll_death_save(attacker.death, rng)
        log.append(f"{attacker.name} death save: {outcome}")
        if attacker.death.dead:
            log.append(f"{attacker.name} dies.")
            return log
        if attacker.death.stable:
            log.append(f"{attacker.name} is stable at 0 HP (unconscious).")
            return log

    # Primary attack(s)
    swings = max(1, int(getattr(attacker.actor, "attacks_per_action", 1)))
    for i in range(swings):
        t1 = _attack_once(
            attacker,
            defender,
            attacker.weapon,
            weapon_idx=weapon_idx,
            armor_idx=armor_idx,
            rng=rng,
            already_loaded_this_turn=used_loading,
        )
        log.extend([f"[Attack {i+1}/{swings}]"] + t1.log)
        defender.hp -= t1.damage
        if t1.damage > 0 and defender.concentration:
            ok, dc = check_concentration_on_damage(
                defender,
                t1.damage,
                rng=rng,
                has_war_caster=has_feat(defender.actor, "War Caster"),
            )
            tag = "maintains" if ok else "drops"
            log.append(f"  concentration {tag} (DC {dc})")
        if defender.hp <= 0 and defender.concentration:
            msg = drop_concentration(defender, "unconscious")
            if msg:
                log.append(f"  {msg}")
        used_loading = used_loading or t1.used_loading
        if defender.hp <= 0 and t1.damage > 0:
            apply_damage_while_down(defender.death, melee_within_5ft=True)
            log.append(f"{defender.name} drops to 0 HP!")
            if defender.death.dead:
                log.append(f"{defender.name} dies.")
            return log

    # Optional off-hand
    t2 = _offhand_if_applicable(
        attacker,
        defender,
        weapon_idx=weapon_idx,
        armor_idx=armor_idx,
        rng=rng,
        already_loaded_this_turn=used_loading,
    )
    log.extend(t2.log)
    defender.hp -= t2.damage
    if t2.damage > 0 and defender.concentration:
        ok, dc = check_concentration_on_damage(
            defender,
            t2.damage,
            rng=rng,
            has_war_caster=has_feat(defender.actor, "War Caster"),
        )
        tag = "maintains" if ok else "drops"
        log.append(f"    concentration {tag} (DC {dc})")
    if defender.hp <= 0 and defender.concentration:
        msg = drop_concentration(defender, "unconscious")
        if msg:
            log.append(f"    {msg}")
    used_loading = used_loading or t2.used_loading
    if defender.hp <= 0 and t2.damage > 0:
        apply_damage_while_down(defender.death, melee_within_5ft=True)
        log.append(f"{defender.name} drops to 0 HP!")
        if defender.death.dead:
            log.append(f"{defender.name} dies.")
    return log


# ---------- encounter ----------
def run_encounter(a: Combatant, b: Combatant, *, seed: int = 42, max_rounds: int = 20) -> Dict[str, object]:
    rng = random.Random(seed)
    widx = WeaponIndex.load(Path("data/weapons.json"))
    aidx = ArmorIndex.load(Path("data/armor.json"))
    first, second, init = roll_initiative(a, b, rng)
    log: List[str] = [f"Initiative — {first.name} vs {second.name}: {init['A']} to {init['B']}"]
    round_no = 1

    while not a.death.dead and not b.death.dead and round_no <= max_rounds:
        log.append(f"— Round {round_no} —")
        # First acts
        log.extend(take_turn(first, second, weapon_idx=widx, armor_idx=aidx, rng=rng))
        if second.death.dead:
            break
        # Second acts
        log.extend(take_turn(second, first, weapon_idx=widx, armor_idx=aidx, rng=rng))
        if first.death.dead:
            break
        round_no += 1

    winner = first.name if second.death.dead else (second.name if first.death.dead else "none")
    return {"winner": winner, "rounds": round_no if winner != "none" else max_rounds, "log": log, "a_hp": a.hp, "b_hp": b.hp}

