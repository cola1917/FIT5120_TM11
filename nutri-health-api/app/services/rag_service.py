"""
RAG Service - recipe retrieval using FAISS vector store.
Uses the project-wide embedding model.
"""

import os
import logging
from typing import List, Dict

from langchain_community.vectorstores import FAISS

from app.services.embedding_provider import get_embeddings

logger = logging.getLogger(__name__)

VECTOR_DB_PATH = "data/food_vector_db"
_FAISS_INDEX = os.path.join(VECTOR_DB_PATH, "index.faiss")


class RAGService:
    def __init__(self):
        self.vectorstore = None
        self.is_ready = False
        self._init_rag()

    def _init_rag(self):
        try:
            if not os.path.isfile(_FAISS_INDEX):
                logger.warning(
                    "FAISS vector store not found (expected %s).",
                    _FAISS_INDEX,
                )
                return

            logger.info("Loading FAISS vector database...")
            try:
                embeddings = get_embeddings()
            except Exception as e:
                logger.error("Failed to load embedding model: %s", e, exc_info=True)
                return

            try:
                self.vectorstore = FAISS.load_local(
                    VECTOR_DB_PATH,
                    embeddings,
                    allow_dangerous_deserialization=True,
                )
            except Exception as e:
                logger.error(
                    "Failed to load FAISS vector store from %s: %s",
                    VECTOR_DB_PATH,
                    e,
                    exc_info=True,
                )
                return

            self.is_ready = True
            logger.info("RAG Service ready")
        except Exception as e:
            logger.error("RAG init failed: %s", e, exc_info=True)

    def retrieve_context(self, food_name: str, goal: str = "grow tall", k: int = 3) -> str:
        """Retrieve relevant recipe context for a given food name."""
        if not self.is_ready:
            return ""

        query = f"{food_name} {goal} nutrition recipe"
        docs = self.vectorstore.similarity_search(query, k=k)

        context = "\n\n".join([doc.page_content for doc in docs])
        return context

    def get_alternatives(self, food_name: str, goal: str = "grow tall", k: int = 3) -> List[Dict]:
        """Get a list of healthier alternative foods."""
        if not self.is_ready:
            return self._get_fallback_alternatives()

        query = f"healthy alternative to {food_name} for kids {goal} nutritious"
        docs = self.vectorstore.similarity_search(query, k=k)

        alternatives = []
        for doc in docs:
            name = doc.metadata.get("name", "")
            if name and name != food_name:
                alternatives.append(
                    {
                        "name": name,
                        "description": self._extract_description(doc.page_content),
                    }
                )

        return alternatives if alternatives else self._get_fallback_alternatives()

    def _extract_description(self, text: str) -> str:
        """Extract a short description from recipe text."""
        if "nutrition:" in text.lower():
            idx = text.lower().find("nutrition:")
            end = text.find("\n", idx)
            return text[idx + 10 : end].strip() if end != -1 else text[idx + 10 :].strip()
        if "ingredients:" in text.lower():
            idx = text.lower().find("ingredients:")
            end = text.find("\n", idx)
            return text[idx + 12 : end].strip()[:30]
        return "A healthy and tasty choice"

    def _get_fallback_alternatives(self) -> List[Dict]:
        return [
            {"name": "Fruit Platter", "description": "Natural sweetness, rich in vitamins"},
            {"name": "Vegetable Salad", "description": "Great source of dietary fibre"},
            {"name": "Plain Yoghurt", "description": "High in calcium and kid-friendly"},
        ]


rag_service = RAGService()
