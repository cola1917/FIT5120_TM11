"""
Pydantic schemas for daily healthy challenge endpoints.
"""

from pydantic import BaseModel, Field


class DailyChallengeTask(BaseModel):
    id: int = Field(..., description="Unique task identifier")
    task_name: str = Field(..., description="Display title of the challenge")
    tips: str = Field(..., description="Short user-facing tip")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "task_name": "Strong Bone Milk",
                "tips": "Drink your milk today!",
            }
        }


class DailyChallengeCompleteRequest(BaseModel):
    id: int = Field(..., description="Task identifier to complete")


class DailyChallengeCompleteResponse(BaseModel):
    id: int = Field(..., description="Unique task identifier")
    task_name: str = Field(..., description="Display title of the challenge")
    feedback: str = Field(..., description="Completion feedback shown to the user")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "task_name": "Strong Bone Milk",
                "feedback": "Your bones are getting hard as rocks!",
            }
        }


class DailyChallengeStatusResponse(BaseModel):
    """Response for checking if user has completed today's challenge."""
    completed_today: bool = Field(..., description="Whether the user has completed today's challenge")
    message: str | None = Field(None, description="Message to display if challenge is completed")

    class Config:
        json_schema_extra = {
            "example": {
                "completed_today": True,
                "message": "Great job! You've completed today's challenge. Come back tomorrow for a new one!",
            }
        }
