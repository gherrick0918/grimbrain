from .core import (
    mod, prof_bonus, ability_mods_from_scores, ArmorProfile,
    ac_calc, resolve_attack_ability, attack_bonus, initiative_bonus,
    roll_attack, roll_damage,
)

from .actions import (
    combine_adv, ActionState, derive_attack_advantage, consume_one_shot_flags,
    apply_dodge, clear_dodge, apply_help, apply_hide,
)

from .saves import save_dc, roll_save
from .conditions import ConditionFlags, derive_condition_advantage, Conditions

__all__ = [
    # Core
    "mod","prof_bonus","ability_mods_from_scores","ArmorProfile",
    "ac_calc","resolve_attack_ability","attack_bonus","initiative_bonus",
    "roll_attack","roll_damage",
    # Actions
    "combine_adv","ActionState","derive_attack_advantage","consume_one_shot_flags",
    "apply_dodge","clear_dodge","apply_help","apply_hide",
    # Saves & Conditions
    "save_dc","roll_save","ConditionFlags","derive_condition_advantage","Conditions",
]
