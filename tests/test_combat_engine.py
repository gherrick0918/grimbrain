from pathlib import Path
from grimbrain.codex.weapons import WeaponIndex
from grimbrain.engine.types import Target
from grimbrain.engine.combat import resolve_attack
import random


class C:
    def __init__(self, str_=16, dex=16, pb=2, styles=None, feats=None, ammo=None):
        self.str_score=str_; self.dex_score=dex; self.proficiency_bonus=pb
        self.fighting_styles=set(styles or [])
        self.proficiencies={"simple weapons","martial weapons"}
        self.feats=set(feats or [])
        self.ammo=dict(ammo or {})
    def ability_mod(self,k): return ({"STR":self.str_score,"DEX":self.dex_score}[k]-10)//2
    def ammo_count(self,t): return int(self.ammo.get(t,0))
    def spend_ammo(self,t,n=1):
        if self.ammo.get(t,0) < n: return False
        self.ammo[t]-=n; return True

def idx(): return WeaponIndex.load(Path("data/weapons.json"))

def test_basic_hit_and_damage_rolls_are_deterministic():
    i=idx(); c=C(dex=18, feats={"Sharpshooter"}, ammo={"arrows":5})  # SS ensures no long-range disadvantage
    tgt = Target(ac=15, hp=10, cover="none", distance_ft=30)
    # Force d20 to 12 (no crit); Longbow AB: +4 DEX +2 PB = +6
    res = resolve_attack(c, "Longbow", tgt, i, base_mode="none", power=False,
                         rng=random.Random(1), forced_d20=(12,7))
    assert res["ok"] and res["is_hit"] and not res["is_crit"]
    assert res["d20"] == 12 and res["attack_bonus"] == 6

def test_crit_doubles_dice_not_mod():
    i=idx(); c=C(str_=16)
    tgt = Target(ac=10, hp=10)
    # Greatsword: 2d6 +3; force nat 20 => crit
    res = resolve_attack(c, "Greatsword", tgt, i, base_mode="none", rng=random.Random(2), forced_d20=(20,5))
    assert res["is_crit"] and res["damage"]["sum_dice"] >= 4  # 4d6 minimum 4
    assert res["damage"]["mod"] == 3

def test_ammo_spend_and_out_of_ammo():
    i=idx(); c=C(dex=16, ammo={"arrows":1})
    tgt = Target(ac=12, hp=10, distance_ft=50)
    # first shot ok
    r1 = resolve_attack(c, "Shortbow", tgt, i, rng=random.Random(3), forced_d20=(15,2))
    assert r1["ok"] and r1["spent_ammo"] and c.ammo["arrows"]==0
    # second shot blocked
    r2 = resolve_attack(c, "Shortbow", tgt, i, rng=random.Random(3), forced_d20=(15,2))
    assert not r2["ok"] and "no arrows" in r2["reason"]

def test_loading_enforced_once_per_turn():
    i=idx(); c=C(dex=16, ammo={"bolts":10})
    tgt = Target(ac=12, hp=10, distance_ft=30)
    # first light crossbow shot allowed
    r1 = resolve_attack(c, "Light Crossbow", tgt, i, has_fired_loading_weapon_this_turn=False,
                        rng=random.Random(4), forced_d20=(10,10))
    assert r1["ok"]
    # second shot in same turn blocked by loading
    r2 = resolve_attack(c, "Light Crossbow", tgt, i, has_fired_loading_weapon_this_turn=True,
                        rng=random.Random(4), forced_d20=(10,10))
    assert not r2["ok"] and "loading" in r2["reason"]

def test_range_and_cover_effects():
    i=idx(); c=C(dex=18, ammo={"arrows":5})  # no Sharpshooter, so long range should impose disadvantage
    tgt_far = Target(ac=15, hp=10, distance_ft=200, cover="half")  # Longbow 150/600
    res = resolve_attack(c, "Longbow", tgt_far, i, base_mode="advantage", rng=random.Random(5), forced_d20=(8,17))
    # advantage + disadvantage -> none; half cover bumps AC by +2
    assert res["effective_ac"] == 17 and res["mode"] == "none"
