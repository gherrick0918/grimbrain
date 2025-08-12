from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Dict, Literal, Optional, Tuple

AdvMode = Literal["normal", "adv", "dis"]

# ---------- Ability & proficiency ---------------------------------------------

def mod(score: int) -> int:
    """5e ability modifier from ability score."""
    return (score - 10) // 2

def prof_bonus(level: int) -> int:
    """5e proficiency bonus by level (SRD table)."""
    if level <= 0:
        return 2
    if level <= 4:
        return 2
    if level <= 8:
        return 3
    if level <= 12:
        return 4
    if level <= 16:
        return 5
    return 6

def ability_mods_from_scores(scores: Dict[str, int]) -> Dict[str, int]:
    """Return {STR,DEX,CON,INT,WIS,CHA} -> modifier."""
    return {k: mod(v) for k, v in scores.items()}

# ---------- Armor Class -------------------------------------------------------

@dataclass(frozen=True)
class ArmorProfile:
    """Armor profile for AC computation."""
    base: int                                  # e.g., 11 for leather, 14 for chain shirt
    kind: Literal["light", "medium", "heavy"]
    dex_cap: Optional[int] = None              # None=unlimited; 2 for medium; 0 for heavy

def ac_calc(armor: ArmorProfile, dex_mod: int, shield_bonus: int = 0, misc: int = 0) -> int:
    if armor.kind == "light":
        dex = dex_mod
    elif armor.kind == "medium":
        cap = 2 if armor.dex_cap is None else armor.dex_cap
        dex = min(dex_mod, cap)
    else:  # heavy
        dex = 0
    return armor.base + dex + shield_bonus + misc

# ---------- Attacks & initiative ---------------------------------------------

def resolve_attack_ability(weapon: Dict) -> Literal["STR", "DEX"]:
    """
    Choose ability for attacks:
      - Ranged or finesse -> DEX
      - Otherwise -> STR
    `weapon` example: {"type":"melee","finesse":True,"ranged":False}
    """
    if weapon.get("ranged"):
        return "DEX"
    if weapon.get("finesse"):
        return "DEX"
    return "STR"

def attack_bonus(ability_mod: int, proficient: bool, level: int, misc: int = 0) -> int:
    return ability_mod + (prof_bonus(level) if proficient else 0) + misc

def initiative_bonus(dex_mod: int, misc: int = 0) -> int:
    return dex_mod + misc

# ---------- Rolling helpers (injectable RNG) ----------------------------------

def _d20(rng) -> int:
    return rng.randint(1, 20)

def roll_attack(to_hit: int, adv: AdvMode = "normal", rng=None) -> Tuple[int, bool, bool, int]:
    """
    Roll a d20 with advantage/disadvantage and add `to_hit`.
    Returns (total, is_crit, is_natural1, face).
    Crit on natural 20. Natural 1 flagged; auto-miss semantics left to engine.
    """
    import random
    rng = rng or random.Random()
    a = _d20(rng)
    if adv == "normal":
        face = a
    else:
        b = _d20(rng)
        face = max(a, b) if adv == "adv" else min(a, b)
    is_crit = face == 20
    is_n1 = face == 1
    return face + to_hit, is_crit, is_n1, face

def roll_damage(
    dice_expr: str,
    mod_val: int = 0,
    crit: bool = False,
    roller: Optional[Callable[[str], int]] = None,
) -> int:
    """
    Roll damage dice + mod. On crit, doubles *dice only* (not the modifier).
    `roller(expr)` should return the result of rolling the dice expression (e.g., "1d8").
    If not provided, uses a minimal internal roller (not guaranteed deterministic).
    """
    def _parse(expr: str) -> Tuple[int, int]:
        n_s, d_s = expr.lower().split("d")
        return int(n_s), int(d_s)

    if roller is None:
        import random
        rnd = random.Random()
        def roller(expr: str) -> int:
            n, d = _parse(expr)
            return sum(rnd.randint(1, d) for _ in range(n))

    dice_total = roller(dice_expr)
    if crit:
        dice_total += roller(dice_expr)
    return dice_total + mod_val
