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
        """Get a list of healthy foods that have Wikimedia images (random selection, not based on input food)."""
        # Whitelist of healthy foods that have guaranteed Wikimedia images
        # Only foods with health_grade A or B are included
        healthy_foods_with_images = [
            {"name": "Apple", "description": "Natural sweetness, rich in vitamins", "grade": "A"},
            {"name": "Banana", "description": "Great source of potassium and energy", "grade": "A"},
            {"name": "Orange", "description": "Packed with vitamin C for immunity", "grade": "A"},
            {"name": "Grape", "description": "Antioxidant-rich and hydrating", "grade": "A"},
            {"name": "Strawberry", "description": "Delicious berries full of vitamins", "grade": "A"},
            {"name": "Watermelon", "description": "Refreshing and hydrating fruit", "grade": "A"},
            {"name": "Broccoli", "description": "Super vegetable with lots of nutrients", "grade": "A"},
            {"name": "Carrot", "description": "Great for eyesight and crunchy fun", "grade": "A"},
            {"name": "Cucumber", "description": "Cool and refreshing vegetable", "grade": "A"},
            {"name": "Tomato", "description": "Juicy and full of lycopene", "grade": "A"},
            {"name": "Spinach", "description": "Iron-rich leafy green", "grade": "A"},
            {"name": "Lettuce", "description": "Light and crispy salad base", "grade": "A"},
            {"name": "Corn", "description": "Sweet kernels with fibre", "grade": "A"},
            {"name": "Avocado", "description": "Creamy healthy fats for growing brains", "grade": "A"},
            {"name": "Blueberry", "description": "Tiny but mighty antioxidant berries", "grade": "A"},
            {"name": "Raspberry", "description": "Tart and sweet nutrient-packed berries", "grade": "A"},
            {"name": "Pear", "description": "Sweet and juicy fibre-rich fruit", "grade": "A"},
            {"name": "Peach", "description": "Soft and sweet summer fruit", "grade": "A"},
            {"name": "Kiwi", "description": "Tropical fruit loaded with vitamin C", "grade": "A"},
            {"name": "Mango", "description": "Sweet tropical delight with vitamins", "grade": "A"},
            {"name": "Pineapple", "description": "Tangy tropical fruit with enzymes", "grade": "A"},
            {"name": "Plum", "description": "Sweet and tart stone fruit", "grade": "A"},
            {"name": "Papaya", "description": "Tropical fruit great for digestion", "grade": "A"},
            {"name": "Beans", "description": "Protein-packed legumes", "grade": "A"},
            {"name": "Salad", "description": "Fresh mixed greens for health", "grade": "A"},
            {"name": "Vegetable Salad", "description": "Great source of dietary fibre", "grade": "A"},
            {"name": "Fruit Platter", "description": "Natural sweetness, rich in vitamins", "grade": "A"},
            {"name": "Plain Yoghurt", "description": "High in calcium and kid-friendly", "grade": "B"},
            {"name": "Grilled Chicken", "description": "Lean protein for strong muscles", "grade": "A"},
            {"name": "Fish", "description": "Omega-3 rich protein for brain health", "grade": "A"},
        ]
        
        # Randomly select k items to ensure variety across scans
        import random
        if len(healthy_foods_with_images) > k:
            selected = random.sample(healthy_foods_with_images, k)
        else:
            selected = healthy_foods_with_images[:k]

        # Return without grade info (frontend doesn't need it)
        return [
            {"name": item["name"], "description": item["description"]}
            for item in selected
        ]

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
