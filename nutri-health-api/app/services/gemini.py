"""
Food image analysis: OpenAI GPT-4o is the primary provider, automatically falls back to
Qwen-VL (DashScope) when the OpenAI quota is exhausted.

Flow:
  1. analyze_food_image()  — vision LLM, outputs child-friendly format directly (~10s)
  2. RAG search            — fast FAISS lookup using food_name (<1s)
  3. rewrite_alternatives() — small LLM call, rewrites only the alternatives list (~2-3s)
"""

import asyncio
import base64
import json
import logging
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

FOOD_ANALYSIS_PROMPT = """
Analyze this food image and provide a child-friendly nutritional assessment for children aged 7-12.

Tone and style rules:
- Warm, lively, and encouraging — like a supportive nutritionist friend
- Simple language that children aged 7-12 can easily understand
- Never use fear-based, negative, or warning language
- Do NOT include any calorie information anywhere

For nutritional_info fields (carbohydrates, protein, fats), each must be an object with:
- "amount": numeric estimate with unit only (e.g. "12.5g")
- "description": one simple sentence explaining what it helps with (no emojis)

For assessment_score (CRITICAL - follow these rules strictly):
- Score 1 (UNHEALTHY): Foods high in sugar, unhealthy fats, or refined carbs with little nutritional value. This includes ALL types of potato chips (bagged Lay's, kettle-cooked, Pringles), french fries, sugary donuts, candy bars, cookies, cakes, pastries, soda, energy drinks, sugary cereals, fried chicken, nuggets, onion rings, cheese puffs, ice cream, and processed meats like hot dogs. These should be rare treats only.
- Score 2 (MODERATE): Foods with some nutritional value but also significant amounts of fat, sugar, salt, or refined carbs. Examples: burgers, pizza, regular pasta, white bread sandwiches, flavored yogurt, sweetened oatmeal, processed snacks. Okay occasionally but not daily.
- Score 3 (HEALTHY): Whole foods rich in nutrients, fiber, vitamins, and minerals. Examples: fruits, vegetables, whole grains, lean proteins, nuts, legumes, dairy, eggs, fish, quinoa, brown rice, unsweetened yogurt. Great for everyday eating.

For assessment:
- Max 3 sentences: praise something good, suggest one pairing, encouraging close
- At most 4 emojis naturally placed

For alternatives:
- Exactly 2 options if the food is unhealthy (score 1) or moderate (score 2), otherwise 0
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
        "food_name": {
            "type": "string",
            "description": "Name of the food item"
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
            "description": "Child-friendly health assessment, max 3 sentences, at most 4 emojis"
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
        "confidence", "food_name", "nutritional_info",
        "assessment_score", "assessment", "alternatives"
    ],
    "additionalProperties": False
}

ALTERNATIVES_REWRITE_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "description": {"type": "string"}
        },
        "required": ["name", "description"],
        "additionalProperties": False
    }
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
    required_fields = ["confidence", "food_name", "nutritional_info", "assessment_score", "assessment"]
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
    #  Alternatives rewrite (small second LLM call)                       #
    # ------------------------------------------------------------------ #

    def _rewrite_alternatives_openai(self, alternatives: list) -> list:
        client = get_openai_client()
        if not client:
            return None

        s = get_dashscope_settings()
        prompt = (
            "Rewrite the descriptions of these food alternatives for children aged 7-12.\n"
            "Rules:\n"
            "- Output at most 2 items — if given more, keep only the best 2\n"
            "- If the name does not start with a food emoji, add one at the beginning\n"
            "- Rewrite 'description' to be simple, warm, and encouraging (1-2 sentences)\n"
            "- No calorie information\n"
            "- Output only the JSON array, nothing else\n\n"
            "Input:\n"
            + json.dumps(alternatives, ensure_ascii=False)
        )

        try:
            completion = client.chat.completions.create(
                model=s.openai_text_model,
                messages=[{"role": "user", "content": prompt}],
            )
            response_text = (completion.choices[0].message.content or "").strip()
            response_text = _unwrap_json_markdown(response_text)
            return json.loads(response_text)
        except Exception as e:
            if _is_quota_exceeded(e):
                raise
            logger.error("OpenAI alternatives rewrite failed: %s", e)
            return alternatives

    def _rewrite_alternatives_qwen(self, alternatives: list) -> list:
        client = get_dashscope_openai_client()
        if not client:
            return alternatives

        s = get_dashscope_settings()
        prompt = (
            "Rewrite the descriptions of these food alternatives for children aged 7-12.\n"
            "Rules:\n"
            "- Output at most 2 items — if given more, keep only the best 2\n"
            "- If the name does not start with a food emoji, add one at the beginning\n"
            "- Rewrite 'description' to be simple, warm, and encouraging (1-2 sentences)\n"
            "- No calorie information\n"
            "- Output only the JSON array, nothing else\n\n"
            "Input:\n"
            + json.dumps(alternatives, ensure_ascii=False)
        )

        try:
            completion = client.chat.completions.create(
                model=s.qwen_text_model,
                messages=[{"role": "user", "content": prompt}],
                stream=False,
            )
            response_text = (completion.choices[0].message.content or "").strip()
            response_text = _unwrap_json_markdown(response_text)
            return json.loads(response_text)
        except Exception as e:
            logger.error("Qwen alternatives rewrite failed: %s", e)
            return alternatives

    async def rewrite_alternatives(self, alternatives: list) -> list:
        """Rewrite only the alternatives list in child-friendly language."""
        if not alternatives:
            return alternatives

        if get_openai_client() is not None:
            try:
                result = await asyncio.to_thread(self._rewrite_alternatives_openai, alternatives)
                if result is not None:
                    return result
            except Exception as e:
                if _is_quota_exceeded(e):
                    logger.warning("OpenAI quota exhausted, switching to Qwen for alternatives rewrite")
                else:
                    logger.error("OpenAI alternatives rewrite error: %s", e)

        logger.info("Using Qwen for alternatives rewrite")
        return await asyncio.to_thread(self._rewrite_alternatives_qwen, alternatives)

    # ------------------------------------------------------------------ #
    #  Fallback response                                                   #
    # ------------------------------------------------------------------ #

    def _get_fallback_response(self) -> Dict[str, Any]:
        return {
            "confidence": 0,
            "food_name": "Food Item",
            "nutritional_info": {
                "carbohydrates": {"amount": "0g", "description": "Helps give you energy to play"},
                "protein": {"amount": "0g", "description": "Helps your muscles grow strong"},
                "fats": {"amount": "0g", "description": "Keeps your brain and body working well"}
            },
            "assessment_score": 1,
            "assessment": "We're having trouble analysing this food right now. Please try again later, or ask a grown-up to help you learn about this food! 🌟",
            "alternatives": [
                {
                    "name": "🍎 Fresh Fruits",
                    "description": "Fruits are always a great choice — naturally sweet and full of goodness!"
                },
                {
                    "name": "🥦 Vegetables",
                    "description": "Colourful veggies help you grow strong and feel great!"
                }
            ]
        }


gemini_service = GeminiService()
