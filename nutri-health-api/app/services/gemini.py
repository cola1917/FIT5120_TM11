"""
Gemini AI Integration Service
Handles food image analysis using Google's Gemini API
"""

import os
import json
import logging
from typing import Dict, Any
from io import BytesIO
from PIL import Image
import google.genai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "PLACEHOLDER_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)


# Prompt template for food analysis
FOOD_ANALYSIS_PROMPT = """
Analyze this food image and provide a comprehensive nutritional assessment suitable for children aged 7-12.

Guidelines:
1. Use simple, child-friendly language
2. Be encouraging and positive
3. If the food is unhealthy, suggest 2-3 healthier alternatives
4. If the food is already healthy, praise it and suggest similar healthy options
5. Nutritional values should be per typical serving size
6. Be specific and accurate with nutritional information
7. Make health assessments educational and not judgmental

Please analyze the image and respond with ONLY the JSON object, no additional text.
"""

ANALYSIS_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "confidence": {
            "type": "number",
            "description": "Your confidence level as a float between 0 and 1 about correctly identifying the food item"
        },
        "food_name": {
            "type": "string",
            "description": "Name of the food item"
        },
        "nutritional_info": {
            "type": "object",
            "properties": {
                "calories": {
                    "type": "integer",
                    "description": "Estimated calories"
                },
                "carbohydrates": {
                    "type": "number",
                    "description": "Grams of carbs"
                },
                "protein": {
                    "type": "number",
                    "description": "Grams of protein"
                },
                "fats": {
                    "type": "number",
                    "description": "Grams of fats"
                }
            },
            "required": ["calories", "carbohydrates", "protein", "fats"],
            "additionalProperties": False
        },
        "assessment_score": {
            "type": "integer",
            "enum": [1, 2, 3],
            "description": "1 = unhealthy, 2 = moderate, 3 = healthy"
        },
        "assessment": {
            "type": "string",
            "description": "A child-friendly explanation of the food's health impact (2-3 sentences)"
        },
        "alternatives": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Healthier alternative name"
                    },
                    "description": {
                        "type": "string",
                        "description": "Why this is a better choice"
                    }
                },
                "required": ["name", "description"],
                "additionalProperties": False
            }
        }
    },
    "required": [
        "confidence",
        "food_name",
        "nutritional_info",
        "assessment_score",
        "assessment",
        "alternatives"
    ],
    "additionalProperties": False
}


class GeminiService:
    """Service for interacting with Google's Gemini API"""
    
    def __init__(self):
        """Initialize Gemini service"""
        self.is_configured = GEMINI_API_KEY != "PLACEHOLDER_KEY"
    
    async def analyze_food_image(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Analyze a food image using Gemini AI.
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            Dictionary containing food analysis results
            
        Raises:
            Exception: If analysis fails
        """
        if not self.is_configured:
            logger.warning("Gemini API key not configured, returning mock data")
            return self._get_fallback_response()
        
        try:
            # Open and validate image
            image = Image.open(BytesIO(image_bytes))
            
            # Ensure image is in RGB mode
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Generate content with the image and prompt
            response = client.models.generate_content(
                model='gemini-3.1-flash-lite-preview',
                contents=[FOOD_ANALYSIS_PROMPT, image],
                config=genai.types.GenerateContentConfig(
                    thinking_config=genai.types.ThinkingConfig(thinking_level='medium'),
                    response_json_schema=ANALYSIS_RESPONSE_SCHEMA
                )
            )

            print('Response:', response.text)
            
            # Extract text from response
            response_text = response.text.strip()
            
            # Try to parse JSON from response
            # Sometimes Gemini wraps JSON in markdown code blocks
            if response_text.startswith("```json"):
                response_text = response_text.split("```json")[1]
                response_text = response_text.split("```")[0]
            elif response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.split("```")[0]
            
            response_text = response_text.strip()
            
            # Parse JSON response
            result = json.loads(response_text)
            
            # Validate response structure
            print('Validating response')
            required_fields = ["confidence", "food_name", "nutritional_info", "assessment_score", "assessment"]
            for field in required_fields:
                if field not in result:
                    logger.error(f"Missing required field: {field}")
                    return self._get_fallback_response()
            
            # Ensure alternatives is a list
            if "alternatives" not in result:
                result["alternatives"] = []
            
            logger.info(f"Successfully analyzed food: {result.get('food_name')}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            logger.error(f"Response text: {response_text}")
            return self._get_fallback_response()
            
        except Exception as e:
            logger.error(f"Error analyzing food image: {e}")
            return self._get_fallback_response()
    
    def _get_fallback_response(self) -> Dict[str, Any]:
        """
        Get a fallback response when Gemini is unavailable or fails.
        
        Returns:
            Dictionary with placeholder data
        """
        return {
            "confidence": 0,
            "food_name": "Food Item",
            "nutritional_info": {
                "calories": 0,
                "carbohydrates": 0.0,
                "protein": 0.0,
                "fats": 0.0
            },
            "assessment_score": 1,
            "assessment": "We're having trouble analyzing this food right now. Please try again later, or ask a grown-up to help you learn about this food! 🌟",
            "alternatives": [
                {
                    "name": "Fresh Fruits",
                    "description": "Fruits are always a great choice with natural sweetness and vitamins!"
                },
                {
                    "name": "Vegetables",
                    "description": "Colorful veggies help you grow strong and healthy!"
                }
            ]
        }


# Create singleton instance
gemini_service = GeminiService()
