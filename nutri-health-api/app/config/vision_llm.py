"""
Alibaba Cloud DashScope — OpenAI-compatible mode (Qwen-VL etc.).

Follows the official example: `OpenAI(api_key=..., base_url=...)`, credentials and URL
are read from environment variables.
Stream, enable_thinking, and thinking_budget are request-level params; only defaults are provided here.

Provider priority: OpenAI -> Qwen-VL (DashScope), automatic fallback on quota exhaustion.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from openai import OpenAI

_API_ROOT = Path(__file__).resolve().parent.parent.parent


class DashScopeOpenAISettings(BaseSettings):
    """DashScope compatible-mode client and Qwen-VL default parameters."""

    model_config = SettingsConfigDict(
        env_file=_API_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    dashscope_api_key: str = ""
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_vl_model: str = "qwen3-vl-plus"
    qwen_text_model: str = "qwen-plus"
    qwen_embedding_model: str = "text-embedding-v3"
    qwen_vl_stream: bool = False
    qwen_vl_enable_thinking: bool = False
    qwen_vl_thinking_budget: int = 81920

    openai_api_key: str = ""
    openai_vision_model: str = "gpt-4o-mini"
    openai_vision_fallback_model: str = "gpt-4o"
    openai_text_model: str = "gpt-4o-mini"

    @property
    def is_configured(self) -> bool:
        return bool(self.dashscope_api_key.strip())


@lru_cache
def get_dashscope_settings() -> DashScopeOpenAISettings:
    return DashScopeOpenAISettings()


def get_dashscope_openai_client() -> Optional["OpenAI"]:
    """Returns None if DASHSCOPE_API_KEY is not set."""
    from openai import OpenAI

    s = get_dashscope_settings()
    if not s.is_configured:
        return None
    return OpenAI(
        api_key=s.dashscope_api_key.strip(),
        base_url=s.dashscope_base_url,
    )


def get_openai_client() -> Optional["OpenAI"]:
    """Returns None if OPENAI_API_KEY is not set."""
    from openai import OpenAI

    s = get_dashscope_settings()
    if not s.openai_api_key.strip():
        return None
    return OpenAI(api_key=s.openai_api_key.strip())


def dashscope_chat_extra_body() -> dict:
    """Returns extra_body dict matching the official example, for use in chat.completions.create."""
    s = get_dashscope_settings()
    return {
        "enable_thinking": s.qwen_vl_enable_thinking,
        "thinking_budget": s.qwen_vl_thinking_budget,
    }
