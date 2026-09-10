"""
rag/router/query_router.py
Lightweight multi-stage query router that normalizes and routes queries across operational complexity tiers.
"""
import re
from typing import Tuple, Dict, Any, Optional
from rag.router.intent_classifier import IntentClassifier, Intent
from rag.router.complexity_classifier import ComplexityClassifier, ComplexityLevel
from rag.router.temporal_router import TemporalRouter

class QueryRouter:
    def __init__(self):
        self.intent_classifier = IntentClassifier()
        self.complexity_classifier = ComplexityClassifier()
        self.temporal_router = TemporalRouter()

    def normalize(self, query: str) -> str:
        """Normalizes whitespace, punctuation, and common variants."""
        q = re.sub(r"\s+", " ", query.strip())
        q = re.sub(r"[?!.,;]+$", "", q)
        return q

    def route(self, query: str) -> Tuple[Intent, ComplexityLevel, str, Dict[str, Any]]:
        """
        Returns (intent, complexity_level, route_name, routing_metadata)
        """
        normalized = self.normalize(query)
        intent, intent_conf = self.intent_classifier.classify(normalized)
        complexity, route_name = self.complexity_classifier.classify(normalized, intent)
        temporal_meta = self.temporal_router.route_temporal_query(normalized)

        metadata = {
            "intent_confidence": intent_conf,
            "normalized_query": normalized,
            "temporal": temporal_meta
        }

        return intent, complexity, route_name, metadata
