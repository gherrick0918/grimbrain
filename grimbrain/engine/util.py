from .types import Combatant
from .campaign import PartyMemberRef
from ..character import Character


def _score(mod: int) -> int:
    return mod * 2 + 10


def make_combatant_from_party_member(p: PartyMemberRef, *, team: str, cid: str) -> Combatant:
    actor = Character(
        str_score=_score(p.str_mod),
        dex_score=_score(p.dex_mod),
        con_score=_score(p.con_mod),
        int_score=_score(p.int_mod),
        wis_score=_score(p.wis_mod),
        cha_score=_score(p.cha_mod),
        proficiency_bonus=p.pb,
        speed_ft=p.speed,
        proficiencies={"simple weapons", "martial weapons"},
        equipped_armor=p.armor,
        equipped_shield=p.shield,
    )
    cmb = Combatant(
        id=cid,
        name=p.name,
        team=team,
        actor=actor,
        hp=p.max_hp,
        weapon=p.weapon_primary or "",
        offhand=p.weapon_offhand,
        ac=p.ac,
        str_mod=p.str_mod,
        dex_mod=p.dex_mod,
        con_mod=p.con_mod,
        int_mod=p.int_mod,
        wis_mod=p.wis_mod,
        cha_mod=p.cha_mod,
        proficiency_bonus=p.pb,
        reach=p.reach,
        speed=p.speed,
        ranged=p.ranged,
        proficient_athletics=p.prof_athletics,
        proficient_acrobatics=p.prof_acrobatics,
        stealth_disadvantage=p.stealth_disadv,
        prof_skills=set(p.prof_skills or []),
        prof_saves=set(p.prof_saves or []),
    )
    return cmb
