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
    # Common enterprise policy abbreviations mapped to their canonical forms
    ENTERPRISE_ACRONYMS = {
        "wfh": "remote work work from home",
        "pto": "paid time off annual leave",
        "pip": "performance improvement plan",
        "da": "daily allowance per diem",
        "opd": "outpatient department medical insurance",
        "nda": "non disclosure agreement confidentiality",
        "posh": "prevention of sexual harassment code of conduct",
        "noc": "no objection certificate",
        "pf": "provident fund",
        "fbp": "flexible benefit plan"
    }

    def __init__(self):
        self.intent_classifier = IntentClassifier()
        self.complexity_classifier = ComplexityClassifier()
        self.temporal_router = TemporalRouter()

    def normalize(self, query: str) -> str:
        """Normalizes whitespace, punctuation, and common variants."""
        q = re.sub(r"\s+", " ", query.strip())
        q = re.sub(r"[?!.,;]+$", "", q)
        return q

    def expand_acronyms(self, query: str) -> str:
        """
        Appends canonical expansions for enterprise acronyms to bridge lexical vocabulary gaps in BM25/Dense retrieval.
        Preserves original query tokens while supplementing domain synonyms.
        """
        words = re.findall(r"\b[a-zA-Z0-9]+\b", query.lower())
        expansions = []
        for w in words:
            if w in self.ENTERPRISE_ACRONYMS:
                expansions.append(self.ENTERPRISE_ACRONYMS[w])
        if expansions:
            return f"{query} ({' '.join(expansions)})"
        return query

    def route(self, query: str, pre_normalized: bool = False) -> Tuple[Intent, ComplexityLevel, str, Dict[str, Any]]:
        """
        Returns (intent, complexity_level, route_name, routing_metadata)
        """
        normalized = query if pre_normalized else self.normalize(query)
        intent, intent_conf = self.intent_classifier.classify(normalized)
        complexity, route_name = self.complexity_classifier.classify(normalized, intent)
        temporal_meta = self.temporal_router.route_temporal_query(normalized)

        metadata = {
            "intent_confidence": intent_conf,
            "normalized_query": normalized,
            "temporal": temporal_meta
        }

        return intent, complexity, route_name, metadata
