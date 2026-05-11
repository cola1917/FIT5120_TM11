from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, field_validator

from app.schemas.recommendation import SUPPORTED_GOALS

VALID_SECTIONS = {"super_power_foods", "tiny_hero_foods", "try_less_foods"}


class ReasonRequest(BaseModel):
    food_name:    str
    category:     str
    section_name: str
    goal_id:      str
    food_id:      str = ""
    likes:        list[str] = []
    dislikes:     list[str] = []

    @field_validator("goal_id")
    @classmethod
    def validate_goal(cls, v: str) -> str:
        if v not in SUPPORTED_GOALS:
            raise ValueError(f"goal_id must be one of {sorted(SUPPORTED_GOALS)}")
        return v

    @field_validator("section_name")
    @classmethod
    def validate_section(cls, v: str) -> str:
        if v not in VALID_SECTIONS:
            raise ValueError(f"section_name must be one of {sorted(VALID_SECTIONS)}")
        return v


class ReasonResponse(BaseModel):
    food_id:   str
    food_name: str
    reason:    str
