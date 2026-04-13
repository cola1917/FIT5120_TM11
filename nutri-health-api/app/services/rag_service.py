"""
RAG Service - recipe retrieval using FAISS vector store.
Uses the project-wide embedding model.
"""

import os
import logging
from typing import List, Dict, Any

from langchain_community.vectorstores import FAISS

from app.services.embedding_provider import get_embeddings
from app.services.alternative_rules import (
    TARGET_ALTERNATIVE_COUNT,
    build_candidate_fact,
    contains_unhealthy_keyword,
    get_fallback_candidate_facts,
    get_rule_based_candidates,
    infer_food_category,
    is_compatible_category,
    normalize_food_name,
)

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

    def get_alternatives(
        self,
        food_name: str,
        goal: str = "grow tall",
        k: int = 6,
        target_count: int = TARGET_ALTERNATIVE_COUNT,
    ) -> List[Dict[str, Any]]:
        """Get healthier alternatives using rules first, then filtered RAG, then fallback facts."""
        source_category = infer_food_category(food_name)
        selected: List[Dict[str, Any]] = []
        seen_names = set()

        rule_candidates = self._filter_candidates(
            get_rule_based_candidates(food_name, limit=max(target_count * 2, 4)),
            food_name,
            source_category,
        )
        self._append_unique(selected, seen_names, rule_candidates, target_count)

        if self.is_ready:
            query = self._build_alternatives_query(food_name, goal, source_category)
            docs = self.vectorstore.similarity_search(query, k=max(k, target_count * 3))
            rag_candidates = self._filter_candidates(
                self._docs_to_candidate_facts(docs),
                food_name,
                source_category,
            )
            self._append_unique(selected, seen_names, rag_candidates, target_count)
        else:
            logger.info("RAG not ready, using rule/fallback alternatives for %s", food_name)

        if len(selected) < target_count:
            fallback_candidates = self._filter_candidates(
                get_fallback_candidate_facts(limit=target_count + 1),
                food_name,
                source_category,
            )
            self._append_unique(selected, seen_names, fallback_candidates, target_count)

        return selected[:target_count]

    def _build_alternatives_query(self, food_name: str, goal: str, source_category: str) -> str:
        return (
            f"healthier kid-friendly substitute for {food_name}. "
            f"Need a same eating context {source_category} option that is lower sugar, "
            f"less processed, more nourishing, and helps kids {goal}. "
            "Prefer whole-food or balanced alternatives, not another junk food."
        )

    def _docs_to_candidate_facts(self, docs: List[Any]) -> List[Dict[str, Any]]:
        candidates: List[Dict[str, Any]] = []
        for doc in docs:
            name = (doc.metadata.get("name", "") or "").strip()
            if not name:
                continue
            candidates.append(
                build_candidate_fact(
                    name=name,
                    description=self._extract_description(doc.page_content),
                    source="rag",
                )
            )
        return candidates

    def _filter_candidates(
        self,
        candidates: List[Dict[str, Any]],
        food_name: str,
        source_category: str,
    ) -> List[Dict[str, Any]]:
        filtered: List[Dict[str, Any]] = []
        normalized_source = normalize_food_name(food_name)

        for candidate in candidates:
            name = (candidate.get("name") or "").strip()
            if not name:
                continue

            normalized_name = normalize_food_name(name)
            if not normalized_name or normalized_name == normalized_source:
                continue

            description = (candidate.get("description") or "").strip()
            candidate_category = candidate.get("candidate_category") or infer_food_category(name)
            combined_text = f"{name} {description}"

            if contains_unhealthy_keyword(combined_text):
                continue
            if self._shares_bad_keyword(normalized_source, normalized_name):
                continue
            if source_category != "general" and not is_compatible_category(source_category, candidate_category):
                continue

            normalized_candidate = dict(candidate)
            normalized_candidate["candidate_category"] = candidate_category
            filtered.append(normalized_candidate)

        return filtered

    def _shares_bad_keyword(self, normalized_source: str, normalized_candidate: str) -> bool:
        shared = set(normalized_source.split()) & set(normalized_candidate.split())
        bad_keywords = {
            "cola", "coke", "soda", "cake", "candy", "chips", "fries", "fried",
            "donut", "doughnut", "pastry", "pizza", "burger",
        }
        return any(token in bad_keywords for token in shared)

    def _append_unique(
        self,
        selected: List[Dict[str, Any]],
        seen_names: set,
        candidates: List[Dict[str, Any]],
        target_count: int,
    ) -> None:
        for candidate in candidates:
            normalized_name = normalize_food_name(candidate.get("name", ""))
            if normalized_name in seen_names:
                continue
            selected.append(candidate)
            seen_names.add(normalized_name)
            if len(selected) >= target_count:
                return

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

rag_service = RAGService()
