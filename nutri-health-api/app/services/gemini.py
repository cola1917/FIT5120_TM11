"""
Food image analysis: OpenAI GPT-4o is the primary provider, automatically falls back to
Qwen-VL (DashScope) when the OpenAI quota is exhausted.

Flow:
  1. analyze_food_image()  — vision LLM, outputs child-friendly format directly (~10s)
"""

import asyncio
import base64
import json
import logging
import os
from io import BytesIO
from typing import Any, Dict, List

from PIL import Image
from dotenv import load_dotenv

from app.config.vision_llm import (
    dashscope_chat_extra_body,
    get_dashscope_openai_client,
    get_dashscope_settings,
    get_openai_client,
)

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mock AI responses for integration testing.
# Set the environment variable MOCK_AI=true (or 1 / yes) to enable mock mode.
# In mock mode no external API calls are made, and deterministic responses are
# returned so that /scan integration tests can run without paid API access.
# This flag is False by default and has no effect on production behaviour.
# ---------------------------------------------------------------------------

MOCK_AI_ANALYSIS: Dict[str, Any] = {
    "confidence": 0.92,
    "is_food": True,
    "food_name": "Apple",
    "primary_object": "apple",
    "reject_reason": "none",
    "nutritional_info": {
        "carbohydrates": {"amount": "14g", "description": "Gives you energy to run and play!"},
        "protein": {"amount": "0.5g", "description": "Helps your muscles grow strong."},
        "fats": {"amount": "0.2g", "description": "Keeps your brain sharp and focused."},
    },
    "assessment_score": 3,
    "assessment": "Apples are a fantastic choice! 🍎 They are packed with vitamins and fibre to keep you going all day. Great job picking a healthy snack! 🌟",
    "alternatives": [],
}


def _is_mock_ai_enabled() -> bool:
    """Return True when the MOCK_AI environment variable is set to a truthy value."""
    return os.getenv("MOCK_AI", "").lower() in ("1", "true", "yes")

FOOD_ANALYSIS_PROMPT = """
Analyze the image and first decide whether the main subject is clearly an edible food item.

Critical recognition rules:
- If the main subject is not edible food, set "is_food" to false
- If the image is a screenshot, UI, phone screen, mouse, keyboard, toy, book, packaging, table object, or other non-food object, set "is_food" to false
- If the image is too blurry, too small, too far away, heavily blocked, or the main subject is unclear, set "is_food" to false
- Do not guess a food name when the image does not clearly show food
- When "is_food" is false, set "food_name" to "__NOT_FOOD__", describe the object in "primary_object", and set "reject_reason" to one of: not_food, screenshot, blurry, unclear, multiple_objects

Tone and style rules:
- Warm, lively, and encouraging — like a supportive nutritionist friend
- Simple language that children aged 7-12 can easily understand
- Never use fear-based, negative, or warning language
- Do NOT include any calorie information anywhere

For nutritional_info fields (carbohydrates, protein, fats), each must be an object with:
- "amount": numeric estimate with unit only (e.g. "12.5g")
- "description": one simple sentence explaining what it helps with (no emojis)

For assessment_score (CRITICAL - this is a best-effort FALLBACK score only, used when catalog matching is unavailable):
- Score 1 (UNHEALTHY): Foods high in sugar, unhealthy fats, or refined carbs with little nutritional value. Examples: donuts, candy, sugary drinks, french fries, potato chips, ice cream, pastries, deep-fried foods. These should be rare treats only.
- Score 2 (MODERATE): Foods with some nutritional value but also significant amounts of fat, sugar, salt, or refined carbs. Examples: burgers, pizza, hot dogs, regular pasta, white bread, processed snacks. Okay occasionally but not daily.
- Score 3 (HEALTHY): Whole foods rich in nutrients, fiber, vitamins, and minerals. Examples: fruits, vegetables, whole grains, lean proteins, nuts, legumes, dairy. Great for everyday eating.

For assessment (this is a fallback child-friendly assessment that may be replaced by backend rules):
- Max 2 sentences: evaluate only the scanned food itself
- Do NOT mention or suggest any other food
- At most 2 emojis naturally placed

For alternatives:
- Exactly 2 options only if the food is unhealthy (score 1) or moderate (score 2), otherwise 0
- Each option must be a genuinely healthier swap, not just a similar-sounding food
- Keep the same eating context when possible: drink -> drink, snack -> snack, dessert -> fruit/dairy/light dessert, fast food -> balanced meal or lighter savory option
- Never suggest another sugary drink, candy, cake, pastry, deep-fried snack, or anything sharing the same junk-food keyword as the original food (example: cola must not become Cola Cake or Cola Candy)
- Each name must start with a relevant food emoji (e.g. "🍎 Apple Slices")
- 1-2 key benefits in child-friendly language in the description

Respond with ONLY the JSON object, no additional text.
"""

ANALYSIS_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "confidence": {
            "type": "number",
            "description": "Confidence level 0-1 about correctly identifying the food item"
        },
        "is_food": {
            "type": "boolean",
            "description": "Whether the image clearly contains an edible food item as the main subject"
        },
        "food_name": {
            "type": "string",
            "description": "Name of the food item"
        },
        "primary_object": {
            "type": "string",
            "description": "Main visible object in the image, e.g. 'mouse', 'pizza', 'phone screen'"
        },
        "reject_reason": {
            "type": "string",
            "enum": ["none", "not_food", "screenshot", "blurry", "unclear", "multiple_objects", "analysis_failed"],
            "description": "Reason for rejecting the image as a valid food scan"
        },
        "nutritional_info": {
            "type": "object",
            "properties": {
                "carbohydrates": {
                    "type": "object",
                    "properties": {
                        "amount": {"type": "string", "description": "e.g. '12.5g'"},
                        "description": {"type": "string", "description": "e.g. 'Helps you run and play all afternoon'"}
                    },
                    "required": ["amount", "description"],
                    "additionalProperties": False
                },
                "protein": {
                    "type": "object",
                    "properties": {
                        "amount": {"type": "string", "description": "e.g. '5.0g'"},
                        "description": {"type": "string", "description": "e.g. 'Builds strong muscles and helps you grow'"}
                    },
                    "required": ["amount", "description"],
                    "additionalProperties": False
                },
                "fats": {
                    "type": "object",
                    "properties": {
                        "amount": {"type": "string", "description": "e.g. '8.0g'"},
                        "description": {"type": "string", "description": "e.g. 'Keeps your brain sharp and body warm'"}
                    },
                    "required": ["amount", "description"],
                    "additionalProperties": False
                }
            },
            "required": ["carbohydrates", "protein", "fats"],
            "additionalProperties": False
        },
        "assessment_score": {
            "type": "integer",
            "enum": [1, 2, 3],
            "description": "1 = unhealthy, 2 = moderate, 3 = healthy"
        },
        "assessment": {
            "type": "string",
            "description": "Child-friendly health assessment of this food only, max 2 sentences, no other food mentioned, at most 2 emojis"
        },
        "alternatives": {
            "type": "array",
            "maxItems": 2,
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Food name starting with a relevant emoji, e.g. '🍎 Apple Slices'"},
                    "description": {"type": "string"}
                },
                "required": ["name", "description"],
                "additionalProperties": False
            }
        }
    },
    "required": [
        "confidence", "is_food", "food_name", "primary_object", "reject_reason", "nutritional_info",
        "assessment_score", "assessment", "alternatives"
    ],
    "additionalProperties": False
}


def _unwrap_json_markdown(response_text: str) -> str:
    text = response_text.strip()
    if text.startswith("```json"):
        text = text.split("```json", 1)[1]
        text = text.split("```", 1)[0]
    elif text.startswith("```"):
        text = text.split("```", 1)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.split("```", 1)[0]
    return text.strip()


def _validate_analysis_core(result: Dict[str, Any]) -> bool:
    required_fields = [
        "confidence",
        "is_food",
        "food_name",
        "primary_object",
        "reject_reason",
        "nutritional_info",
        "assessment_score",
        "assessment",
    ]
    return all(field in result for field in required_fields)


def _is_low_quality(result: Dict[str, Any]) -> bool:
    """Return True if the vision result is too low quality to use."""
    if result.get("confidence", 1) < 0.6:
        return True
    if result.get("food_name", "").strip().lower() in ("", "food item"):
        return True
    return False


def _is_quota_exceeded(error: Exception) -> bool:
    """Return True if the error indicates an OpenAI quota exhaustion."""
    try:
        from openai import RateLimitError
        if isinstance(error, RateLimitError):
            code = getattr(error, "code", None) or ""
            body = str(error)
            return "insufficient_quota" in code or "insufficient_quota" in body
    except ImportError:
        pass
    return False



class GeminiService:
    """Food scanner: OpenAI first, automatic fallback to Qwen-VL on quota exhaustion."""

    # ------------------------------------------------------------------ #
    #  Image analysis                                                      #
    # ------------------------------------------------------------------ #

    def _analyze_food_image_openai(self, image_bytes: bytes, model: str = None) -> Dict[str, Any]:
        client = get_openai_client()
        if not client:
            return None

        s = get_dashscope_settings()
        use_model = model or s.openai_vision_model
        response_text = ""
        try:
            image = Image.open(BytesIO(image_bytes))
            if image.mode != "RGB":
                image = image.convert("RGB")
            image.thumbnail((512, 512), Image.LANCZOS)
            buf = BytesIO()
            image.save(buf, format="JPEG")
            b64 = base64.standard_b64encode(buf.getvalue()).decode("ascii")
            data_url = f"data:image/jpeg;base64,{b64}"

            schema_hint = (
                "\n\nRespond with ONLY one JSON object (no markdown) matching this schema:\n"
                + json.dumps(ANALYSIS_RESPONSE_SCHEMA, ensure_ascii=False)
            )
            user_text = FOOD_ANALYSIS_PROMPT.strip() + schema_hint

            completion = client.chat.completions.create(
                model=use_model,
                messages=[{"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": data_url}},
                    {"type": "text", "text": user_text},
                ]}],
            )
            response_text = (completion.choices[0].message.content or "").strip()
            response_text = _unwrap_json_markdown(response_text)
            result = json.loads(response_text)
            if not _validate_analysis_core(result):
                logger.error("OpenAI response JSON is missing required fields")
                return self._get_fallback_response()
            if "alternatives" not in result:
                result["alternatives"] = []
            logger.info("OpenAI analysis succeeded (%s): %s", use_model, result.get("food_name"))
            return result
        except Exception as e:
            if _is_quota_exceeded(e):
                raise
            logger.error("OpenAI image analysis failed (%s): %s", use_model, e)
            return self._get_fallback_response()

    def _analyze_food_image_qwen(self, image_bytes: bytes) -> Dict[str, Any]:
        client = get_dashscope_openai_client()
        if not client:
            return self._get_fallback_response()

        s = get_dashscope_settings()
        response_text = ""
        try:
            image = Image.open(BytesIO(image_bytes))
            if image.mode != "RGB":
                image = image.convert("RGB")
            image.thumbnail((512, 512), Image.LANCZOS)

            fmt = (image.format or "JPEG").upper()
            mime = "image/png" if fmt == "PNG" else "image/jpeg"
            buf = BytesIO()
            save_fmt = "PNG" if mime == "image/png" else "JPEG"
            image.save(buf, format=save_fmt)
            b64 = base64.standard_b64encode(buf.getvalue()).decode("ascii")
            data_url = f"data:{mime};base64,{b64}"

            schema_hint = (
                "\n\nRespond with ONLY one JSON object (no markdown) matching this schema:\n"
                + json.dumps(ANALYSIS_RESPONSE_SCHEMA, ensure_ascii=False)
            )
            user_text = FOOD_ANALYSIS_PROMPT.strip() + schema_hint

            content: List[Dict[str, Any]] = [
                {"type": "image_url", "image_url": {"url": data_url}},
                {"type": "text", "text": user_text},
            ]

            extra = dashscope_chat_extra_body()
            if s.qwen_vl_stream:
                stream = client.chat.completions.create(
                    model=s.qwen_vl_model,
                    messages=[{"role": "user", "content": content}],
                    stream=True,
                    extra_body=extra,
                )
                parts: List[str] = []
                for chunk in stream:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta
                    if delta is None:
                        continue
                    c = getattr(delta, "content", None) or ""
                    if c:
                        parts.append(c)
                response_text = "".join(parts).strip()
            else:
                completion = client.chat.completions.create(
                    model=s.qwen_vl_model,
                    messages=[{"role": "user", "content": content}],
                    stream=False,
                    extra_body=extra,
                )
                msg = completion.choices[0].message
                response_text = (msg.content or "").strip()

            response_text = _unwrap_json_markdown(response_text)
            result = json.loads(response_text)
            if not _validate_analysis_core(result):
                logger.error("Qwen response JSON is missing required fields")
                return self._get_fallback_response()
            if "alternatives" not in result:
                result["alternatives"] = []
            logger.info("Qwen-VL analysis succeeded: %s", result.get("food_name"))
            return result
        except json.JSONDecodeError as e:
            logger.error("Failed to parse Qwen image analysis JSON: %s", e)
            logger.error("Raw response text: %s", response_text[:2000] if response_text else "")
            return self._get_fallback_response()
        except Exception as e:
            logger.error("Qwen image analysis failed: %s", e)
            return self._get_fallback_response()

    async def analyze_food_image(self, image_bytes: bytes) -> Dict[str, Any]:
        if _is_mock_ai_enabled():
            logger.info("MOCK_AI enabled: returning deterministic mock food analysis (no external calls)")
            return {**MOCK_AI_ANALYSIS}

        if get_openai_client() is not None:
            try:
                s = get_dashscope_settings()
                result = await asyncio.to_thread(self._analyze_food_image_openai, image_bytes)
                if result is not None:
                    if _is_low_quality(result) and s.openai_vision_fallback_model != s.openai_vision_model:
                        logger.info(
                            "Low quality result from %s (confidence=%.2f, food_name=%r), retrying with %s",
                            s.openai_vision_model,
                            result.get("confidence", 0),
                            result.get("food_name"),
                            s.openai_vision_fallback_model,
                        )
                        retry = await asyncio.to_thread(
                            self._analyze_food_image_openai, image_bytes, s.openai_vision_fallback_model
                        )
                        if retry is not None:
                            return retry
                    return result
            except Exception as e:
                if _is_quota_exceeded(e):
                    logger.warning("OpenAI quota exhausted, switching to Qwen-VL")
                else:
                    logger.error("OpenAI image analysis error: %s", e)

        logger.info("Using Qwen-VL for image analysis")
        return await asyncio.to_thread(self._analyze_food_image_qwen, image_bytes)

    # ------------------------------------------------------------------ #
    #  Fallback response                                                   #
    # ------------------------------------------------------------------ #

    def _get_fallback_response(self) -> Dict[str, Any]:
        return {
            "confidence": 0,
            "is_food": False,
            "food_name": "__NOT_FOOD__",
            "primary_object": "unknown",
            "reject_reason": "analysis_failed",
            "nutritional_info": {
                "carbohydrates": {"amount": "0g", "description": "Helps give you energy to play"},
                "protein": {"amount": "0g", "description": "Helps your muscles grow strong"},
                "fats": {"amount": "0g", "description": "Keeps your brain and body working well"}
            },
            "assessment_score": 1,
            "assessment": "We're having trouble analysing this food right now. Please try again later, or ask a grown-up to help you learn about this food! 🌟",
            "alternatives": []
        }


gemini_service = GeminiService()
