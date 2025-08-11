from pydantic import BaseModel
from typing import List

class NamedText(BaseModel):
    name: str
    text: str

class MonsterSidecar(BaseModel):
    name: str
    source: str
    ac: str
    hp: str
    speed: str
    str: int
    dex: int
    con: int
    int: int
    wis: int
    cha: int
    traits: List[NamedText]
    actions: List[NamedText]
    reactions: List[NamedText]
    provenance: List[str]

class SpellSidecar(BaseModel):
    name: str
    level: int
    school: str
    casting_time: str
    range: str
    components: str
    duration: str
    classes: List[str]
    text: str
    provenance: List[str]
