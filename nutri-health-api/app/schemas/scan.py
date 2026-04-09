"""
Pydantic Schemas for Scan Endpoint
Request and response models with validation
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class NutritionalInfo(BaseModel):
    """Nutritional information for a food item.
    Each field is a two-line string: numeric estimate on the first line,
    child-friendly explanation on the second line.
    """
    carbohydrates: Optional[str] = Field(None, description="Carbohydrates — value and description")
    protein: Optional[str] = Field(None, description="Protein — value and description")
    fats: Optional[str] = Field(None, description="Fats — value and description")

    class Config:
        extra = "allow"


class Alternative(BaseModel):
    """Healthier alternative suggestion"""
    name: str = Field(..., description="Name of the alternative food")
    description: Optional[str] = Field(None, description="Child-friendly description of benefits")

    class Config:
        extra = "allow"


class ScanResponse(BaseModel):
    """Response from the /scan endpoint"""
    recognised: bool = Field(..., description="Whether the food was successfully identified")
    confidence: float = Field(..., description="Confidence score 0-1")
    food_name: str = Field(..., description="Identified food name")
    nutritional_info: NutritionalInfo = Field(..., description="Nutritional breakdown")
    assessment_score: int = Field(..., description="Health score: 1=unhealthy, 2=moderate, 3=healthy")
    assessment: str = Field(..., description="Child-friendly health assessment")
    alternatives: List[Alternative] = Field(default_factory=list, description="Healthier alternatives")

    class Config:
        json_schema_extra = {
            "example": {
                "confidence": 0.95,
                "food_name": "Chocolate Chip Cookie",
                "nutritional_info": {
                    "carbohydrates": "20.0g\nGives you a quick burst of energy to run and play",
                    "protein": "2.0g\nHelps your muscles stay strong",
                    "fats": "7.0g\nKeeps your brain sharp and body warm"
                },
                "assessment_score": 1,
                "assessment": "This cookie tastes amazing as an occasional treat! 🍪 Try pairing it with a glass of milk for some extra goodness. You're doing great exploring different foods! 😊",
                "alternatives": [
                    {
                        "name": "Oatmeal Raisin Cookie",
                        "description": "Made with oats that give you longer-lasting energy and keep you full."
                    },
                    {
                        "name": "Apple Slices with Peanut Butter",
                        "description": "A naturally sweet snack that also helps build strong muscles."
                    }
                ]
            }
        }


class ErrorResponse(BaseModel):
    """Error response model"""
    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="INVALID_FILE | ANALYSIS_FAILED | AUTH_FAILED")

    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Failed to process image",
                "error_code": "ANALYSIS_FAILED"
            }
        }
