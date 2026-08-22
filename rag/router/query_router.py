import re
from typing import Tuple

class QueryIntent:
    FACT = "fact"
    COMPARISON = "comparison"
    TEMPORAL = "temporal"
    COMPLEX = "complex"

class ComplexityLevel:
    L0 = 0  # Deterministic SQL fact
    L1 = 1  # Precomputed QA
    L2 = 2  # Hybrid retrieval
    L3 = 3  # Comparison/temporal (deterministic diff)
    L4 = 4  # Complex reasoning (→ LLM)

class QueryRouter:
    """
    Three-tier routing hierarchy:
    1. Deterministic keyword rules
    2. Intent matching
    """
    
    FACT_PATTERNS = [
        r"\b(how many|how much|what is the|when is|who is|eligible)\b",
        r"\b(maximum|minimum|limit|ceiling|entitlement)\b",
        r"\b(effective date|expiry|notice period)\b",
    ]
    COMPARE_PATTERNS = [
        r"\b(compare|diff|changed|difference between|previous version|old policy)\b",
    ]
    TEMPORAL_PATTERNS = [
        r"\b(before|after|during|as of|since|until|in \d{4}|last year)\b",
    ]
    
    def __init__(self):
        self.fact_regex = re.compile("|".join(self.FACT_PATTERNS), re.IGNORECASE)
        self.compare_regex = re.compile("|".join(self.COMPARE_PATTERNS), re.IGNORECASE)
        self.temporal_regex = re.compile("|".join(self.TEMPORAL_PATTERNS), re.IGNORECASE)

    def route(self, query: str) -> Tuple[str, int]:
        """Returns (intent, complexity)"""
        # Highest priority: Comparison
        if self.compare_regex.search(query):
            return QueryIntent.COMPARISON, ComplexityLevel.L3
            
        # Temporal
        if self.temporal_regex.search(query):
            return QueryIntent.TEMPORAL, ComplexityLevel.L3
            
        # Fact
        if self.fact_regex.search(query):
            return QueryIntent.FACT, ComplexityLevel.L0
            
        # Default fallback to complex RAG
        return QueryIntent.COMPLEX, ComplexityLevel.L4
