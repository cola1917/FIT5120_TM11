from __future__ import annotations

from pydantic import BaseModel, computed_field, field_validator


SUPPORTED_GOALS = {"grow", "see", "think", "fight", "feel", "strong"}


class RecommendationRequest(BaseModel):
    goal_id: str
    likes: list[str] = []
    dislikes: list[str] = []
    blacklist: list[str] = []   # foods the user cannot / will not eat
    allergies: list[str] = []   # allergy items (separate from blacklist)

    @field_validator("goal_id")
    @classmethod
    def validate_goal(cls, v: str) -> str:
        if v not in SUPPORTED_GOALS:
            raise ValueError(f"goal_id must be one of {sorted(SUPPORTED_GOALS)}")
        return v


class EnrichedFoodItem(BaseModel):
    food_id: str          # url-safe slug of food_name, used as React key
    food_name: str        # food name chosen by the model
    category: str         # inferred food category
    image_url: str        # /static/category_fallback/{category}.png
    image_status: str     # "fallback" | "generated"
    reason: str           # child-friendly explanation from the model

    # Old frontend-compatible aliases (computed, included in serialized JSON)
    @computed_field
    @property
    def cn_code(self) -> str:
        return self.food_id

    @computed_field
    @property
    def name(self) -> str:
        return self.food_name

    @computed_field
    @property
    def grade(self) -> str:
        return self.reason


class RecommendationResponse(BaseModel):
    super_power_foods: list[EnrichedFoodItem]
    tiny_hero_foods: list[EnrichedFoodItem]
    try_less_foods: list[EnrichedFoodItem]
