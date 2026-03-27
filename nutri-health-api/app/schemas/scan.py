"""
Pydantic Schemas for Scan Endpoint
Request and response models with validation
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class NutritionalInfo(BaseModel):
    """Nutritional information for a food item"""
    calories: Optional[int] = Field(None, description="Calories in kcal")
    carbohydrates: Optional[float] = Field(None, description="Carbohydrates in grams")
    protein: Optional[float] = Field(None, description="Protein in grams")
    fats: Optional[float] = Field(None, description="Fats in grams")
    
    # Allow additional fields
    class Config:
        extra = "allow"


class Alternative(BaseModel):
    """Healthier alternative suggestion"""
    name: str = Field(..., description="Name of the alternative food")
    description: Optional[str] = Field(None, description="Description of why it's healthier")
    
    # Allow additional fields
    class Config:
        extra = "allow"


class ScanResponse(BaseModel):
    """Response from the /scan endpoint"""
    confidence: float = Field(..., description="Confidence")
    food_name: str = Field(..., description="Identified food name")
    nutritional_info: NutritionalInfo = Field(..., description="Nutritional breakdown")
    assessment_score: int = Field(..., description="Health score")
    assessment: str = Field(..., description="Assessment and recommendations")
    alternatives: List[Alternative] = Field(default_factory=list, description="Healthier alternatives")
    
    class Config:
        json_schema_extra = {
            "example": {
                "confidence": 0.95,
                "food_name": "Chocolate Chip Cookie",
                "nutritional_info": {
                    "calories": 150,
                    "carbohydrates": 20.0,
                    "protein": 2.0,
                    "fats": 7.0
                },
                "assessment_score": 1,
                "assessment": "This cookie is high in sugar and fats. While it's okay as an occasional treat, it shouldn't be eaten every day. Try to balance it with healthier snacks like fruits!",
                "alternatives": [
                    {
                        "name": "Oatmeal Raisin Cookie",
                        "description": "Contains oats which provide fiber and sustained energy"
                    },
                    {
                        "name": "Apple Slices with Peanut Butter",
                        "description": "Natural sweetness with protein and healthy fats"
                    }
                ]
            }
        }


class ErrorResponse(BaseModel):
    """Error response model"""
    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code for client handling")
    
    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Failed to process image",
                "error_code": "PROCESSING_ERROR"
            }
        }
