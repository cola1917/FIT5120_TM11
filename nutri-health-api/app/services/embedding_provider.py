"""
Embedding provider: uses BAAI/bge-m3.
"""

from __future__ import annotations

import logging
import os

from app.load_env import ensure_dotenv_loaded
from langchain_core.embeddings import Embeddings
from langchain_huggingface import HuggingFaceEmbeddings

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "BAAI/bge-m3"


def get_embeddings() -> Embeddings:
    ensure_dotenv_loaded()
    model_name = os.getenv("EMBEDDING_MODEL_NAME", DEFAULT_MODEL).strip()
    logger.info("Loading embedding model: %s", model_name)
    return HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={"trust_remote_code": True},
    )
