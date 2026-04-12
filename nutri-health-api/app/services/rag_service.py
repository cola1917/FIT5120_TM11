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
        """Get a list of healthy foods (random selection, not based on input food)."""
        if not self.is_ready:
            return self._get_fallback_alternatives()

        # Get all healthy foods (grade A or B) from the vector store
        # We do a broad search to get diverse healthy options
        query = f"healthy nutritious food for kids {goal} fruits vegetables whole grains lean protein"
        docs = self.vectorstore.similarity_search(query, k=20)

        # Filter for only A and B grade foods and collect unique ones
        healthy_foods = []
        seen_names = set()
        for doc in docs:
            name = doc.metadata.get("name", "")
            grade = doc.metadata.get("health_grade", "")
            if name and grade in ["A", "B"] and name not in seen_names:
                seen_names.add(name)
                healthy_foods.append(
                    {
                        "name": name,
                        "description": self._extract_description(doc.page_content),
                        "grade": grade,
                    }
                )

        # If we don't have enough from similarity search, add fallback options
        if len(healthy_foods) < k:
            fallbacks = [
                {"name": "Fruit Platter", "description": "Natural sweetness, rich in vitamins", "grade": "A"},
                {"name": "Vegetable Salad", "description": "Great source of dietary fibre", "grade": "A"},
                {"name": "Plain Yoghurt", "description": "High in calcium and kid-friendly", "grade": "B"},
                {"name": "Whole Grain Bread", "description": "Long-lasting energy from whole grains", "grade": "A"},
                {"name": "Grilled Chicken", "description": "Lean protein for strong muscles", "grade": "A"},
            ]
            for fb in fallbacks:
                if fb["name"] not in seen_names:
                    healthy_foods.append(fb)
                    if len(healthy_foods) >= k + 5:
                        break

        # Randomly select k items to ensure variety across scans
        import random
        if len(healthy_foods) > k:
            selected = random.sample(healthy_foods, k)
        else:
            selected = healthy_foods[:k]

        # Return without grade info (frontend doesn't need it)
        return [
            {"name": item["name"], "description": item["description"]}
            for item in selected
        ] if selected else self._get_fallback_alternatives()

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
