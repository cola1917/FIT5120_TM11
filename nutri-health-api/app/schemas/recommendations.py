"""
Pydantic schemas for the /recommendations endpoint.
"""

from pydantic import BaseModel, Field


class RecommendationRequest(BaseModel):
    goal_id: str = Field(..., description="Goal identifier: grow | see | think | fight | feel | strong")
    likes: list[str] = Field(default=[], description="API preference IDs the user likes")
    dislikes: list[str] = Field(default=[], description="API preference IDs the user dislikes")
    blacklist: list[str] = Field(default=[], description="Allergen/food items to exclude globally")

    class Config:
        json_schema_extra = {
            "example": {
                "goal_id": "grow",
                "likes": ["dairy", "meat", "vegetables"],
                "dislikes": ["fish"],
                "blacklist": ["egg", "nuts"],
            }
        }


class FoodItem(BaseModel):
    cn_code: int = Field(..., description="Primary key from cn_fdes")
    name: str = Field(..., description="Food name (first segment of descriptor)")
    category: str = Field(..., description="Preference ID this food belongs to")
    grade: str = Field(..., description="Health grade: A | B | D | E")
    image_url: str = Field(..., description="Pollinations AI generated image URL")

    class Config:
        json_schema_extra = {
            "example": {
                "cn_code": 1042,
                "name": "Chicken breast",
                "category": "meat",
                "grade": "A",
                "image_url": "https://image.pollinations.ai/prompt/Chicken%20breast%20food%20photography%20white%20background?model=flux&width=400&height=400&nologo=true",
            }
        }


class RecommendationResponse(BaseModel):
    super_power_foods: list[FoodItem] = Field(..., description="Up to 3 healthy foods from liked + goal categories")
    tiny_hero_foods: list[FoodItem] = Field(..., description="Up to 3 healthy foods from disliked / unexplored goal categories")
    try_less_foods: list[FoodItem] = Field(..., description="Up to 3 unhealthy foods from liked / goal categories")

    class Config:
        json_schema_extra = {
            "example": {
                "super_power_foods": [],
                "tiny_hero_foods": [],
                "try_less_foods": [],
            }
        }
