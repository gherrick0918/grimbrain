from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Optional


class Quest(BaseModel):
    id: str
    title: str
    steps: List[str] = []


class Campaign(BaseModel):
    name: str = Field(min_length=1)
    party: List[str]
    packs: List[str] = []
    quests: List[Quest] = []


__all__ = ["Quest", "Campaign"]

