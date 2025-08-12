from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import json
import yaml
from pydantic import BaseModel, Field

from .models import PC, Attack


class PCSheetAttack(BaseModel):
    name: str
    damage_dice: str
    type: str
    ability: str
    proficient: bool = True
    to_hit: int | None = None
    save_dc: int | None = None
    save_ability: str | None = None


class PCSheet(BaseModel):
    name: str
    class_: str = Field(alias="class")
    level: int
    abilities: Dict[str, int]
    ac: int = 10
    hp: int = 1
    prof_bonus: int | None = None
    saves: Dict[str, int] = Field(default_factory=dict)
    skills: Dict[str, int] = Field(default_factory=dict)
    attacks: List[PCSheetAttack] = Field(default_factory=list)
    prepared_spells: List[Dict[str, Any]] = Field(default_factory=list)
    resources: Dict[str, Any] = Field(default_factory=dict)

    @property
    def pb(self) -> int:
        return self.prof_bonus if self.prof_bonus is not None else 2 + (self.level - 1) // 4

    def to_pc(self) -> PC:
        atks: List[Attack] = []
        for atk in self.attacks:
            to_hit = atk.to_hit if atk.to_hit is not None else attack_to_hit(self, atk)
            save_dc = atk.save_dc
            if save_dc is None and atk.save_ability:
                save_dc = spell_save_dc(self, atk.save_ability)
            atks.append(Attack(name=atk.name, damage_dice=atk.damage_dice, type=atk.type, to_hit=to_hit, save_dc=save_dc, save_ability=atk.save_ability))
        return PC(name=self.name, ac=self.ac, hp=self.hp, attacks=atks)


def ability_mod(score: int) -> int:
    return (score - 10) // 2


def spell_save_dc(pc: PCSheet, ability: str = "int") -> int:
    return 8 + ability_mod(pc.abilities.get(ability, 10)) + pc.pb


def attack_to_hit(pc: PCSheet, attack: PCSheetAttack) -> int:
    mod = ability_mod(pc.abilities.get(attack.ability, 10))
    if attack.proficient:
        mod += pc.pb
    return mod


def load_pc_sheet(path: str | Path) -> PCSheet:
    path = Path(path)
    text = path.read_text()
    data: Dict[str, Any]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = yaml.safe_load(text)
    return PCSheet(**data)
