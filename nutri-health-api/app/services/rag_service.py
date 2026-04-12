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
        """Get a list of healthy foods that have Wikimedia images (random selection, not based on input food).
        
        IMPORTANT: Food names must EXACTLY match the keys in scan.py's wikimedia_food_map dictionary.
        Only use lowercase names that are guaranteed to have images.
        """
        # Whitelist of healthy foods with EXACT name matching to wikimedia_food_map in scan.py
        # All names must be lowercase to match the mapping dictionary
        healthy_foods_with_images = [
            {"name": "apple", "description": "Natural sweetness, rich in vitamins"},
            {"name": "banana", "description": "Great source of potassium and energy"},
            {"name": "orange", "description": "Packed with vitamin C for immunity"},
            {"name": "grape", "description": "Antioxidant-rich and hydrating"},
            {"name": "strawberry", "description": "Delicious berries full of vitamins"},
            {"name": "watermelon", "description": "Refreshing and hydrating fruit"},
            {"name": "broccoli", "description": "Super vegetable with lots of nutrients"},
            {"name": "carrot", "description": "Great for eyesight and crunchy fun"},
            {"name": "cucumber", "description": "Cool and refreshing vegetable"},
            {"name": "tomato", "description": "Juicy and full of lycopene"},
            {"name": "spinach", "description": "Iron-rich leafy green"},
            {"name": "lettuce", "description": "Light and crispy salad base"},
            {"name": "corn", "description": "Sweet kernels with fibre"},
            {"name": "avocado", "description": "Creamy healthy fats for growing brains"},
            {"name": "blueberry", "description": "Tiny but mighty antioxidant berries"},
            {"name": "raspberry", "description": "Tart and sweet nutrient-packed berries"},
            {"name": "pear", "description": "Sweet and juicy fibre-rich fruit"},
            {"name": "peach", "description": "Soft and sweet summer fruit"},
            {"name": "kiwi", "description": "Tropical fruit loaded with vitamin C"},
            {"name": "mango", "description": "Sweet tropical delight with vitamins"},
            {"name": "pineapple", "description": "Tangy tropical fruit with enzymes"},
            {"name": "plum", "description": "Sweet and tart stone fruit"},
            {"name": "papaya", "description": "Tropical fruit great for digestion"},
            {"name": "beans", "description": "Protein-packed legumes"},
            {"name": "salad", "description": "Fresh mixed greens for health"},
            {"name": "vegetable salad", "description": "Great source of dietary fibre"},
            {"name": "fruit platter", "description": "Natural sweetness, rich in vitamins"},
            {"name": "plain yoghurt", "description": "High in calcium and kid-friendly"},
            {"name": "grilled chicken", "description": "Lean protein for strong muscles"},
            {"name": "fish", "description": "Omega-3 rich protein for brain health"},
        ]
        
        # Randomly select k items to ensure variety across scans
        import random
        if len(healthy_foods_with_images) > k:
            selected = random.sample(healthy_foods_with_images, k)
        else:
            selected = healthy_foods_with_images[:k]

        # Return exactly as defined - names must match wikimedia_food_map keys
        return selected

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
