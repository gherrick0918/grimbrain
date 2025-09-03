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
from .types import Target, Cover


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


def _roll_d20(rng: random.Random) -> int:
    """Roll a single d20 using ``rng``."""
    return rng.randint(1, 20)


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


def _effective_ac(ac: int, cover: Cover, has_sharp: bool) -> int:
    if cover == "total":
        return 10**9
    bump = 0 if (has_sharp and cover in {"half", "three-quarters"}) else _COVER_TO_AC.get(cover, 0)
    return ac + bump


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
) -> Dict[str, Any]:
    """Resolve a single weapon attack.

    Returns a dictionary with roll breakdown and outcome. The attacker's
    ammo is reduced when appropriate, but no other character state is
    mutated.
    """

    rng = rng or random.Random()
    w = weapon_index.get(weapon_name)
    notes: List[str] = []

    # Loading gate
    if w.has_prop("loading") and has_fired_loading_weapon_this_turn:
        return {
            "ok": False,
            "reason": "loading (already fired this turn)",
            "notes": ["loading"],
            "spent_ammo": False,
        }

    # Range/cover adjustments
    mode = base_mode
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

    # Attack bonus and d20 roll
    ab = attack_bonus(attacker, w, power=power)

    if forced_d20:
        candidates = forced_d20
    else:
        d1 = _roll_d20(rng)
        d2 = _roll_d20(rng)
        candidates = (d1, d2)

    if mode == "advantage":
        d = max(candidates)
    elif mode == "disadvantage":
        d = min(candidates)
    else:
        d = candidates[0]

    is_hit, is_crit = roll_outcome(d, ab, eff_ac)

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

