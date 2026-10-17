"""
rag/router/intent_classifier.py
Classifies user query intent across 7 distinct operational routes.
"""
import re
from enum import Enum
from typing import Tuple, Dict, Any

class Intent(str, Enum):
    FACT = "FACT"
    COMPILED_QA = "COMPILED_QA"
    SEARCH = "SEARCH"
    COMPARISON = "COMPARISON"
    TEMPORAL = "TEMPORAL"
    MULTI_POLICY = "MULTI_POLICY"
    REASONING = "REASONING"
    UNKNOWN = "UNKNOWN"

class IntentClassifier:
    COMPARISON_PATTERNS = [
        re.compile(r"\b(?:compare|difference|changed|changes|versus|vs|diff|updated from|between v\d+ and v\d+)\b", re.IGNORECASE),
        re.compile(r"\bwhat changed\b", re.IGNORECASE),
        re.compile(r"\bhow is .* different from\b", re.IGNORECASE)
    ]
    
    TEMPORAL_PATTERNS = [
        re.compile(r"\b(?:in 20\d\d|as of|effective date|historical|previous version|prior policy|back in|when was .* enacted|old version)\b", re.IGNORECASE),
        re.compile(r"\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+20\d\d\b", re.IGNORECASE),
        re.compile(r"\bv\d+\b", re.IGNORECASE)
    ]
    
    FACT_PATTERNS = [
        re.compile(r"\b(?:how many|how much|what is the limit|maximum amount|per diem|number of days|working hours|notice period|probation period|gift limit)\b", re.IGNORECASE),
        re.compile(r"\b(?:what is the (?:amount|percentage|threshold|allowance|entitlement)|daily allowance|metro allowance|internet allowance)\b", re.IGNORECASE)
    ]
    
    REASONING_PATTERNS = [
        re.compile(r"\b(?:what if|suppose|scenario|if i transfer|how does .* affect|consequences|exception to|is it allowed if)\b", re.IGNORECASE),
        re.compile(r"\b(?:eligible if|can i also|hypothetical)\b", re.IGNORECASE)
    ]

    MULTI_POLICY_PATTERNS = [
        re.compile(r"\b(?:both|and also|across policies|travel and expense.*leave|security.*conduct)\b", re.IGNORECASE)
    ]

    OPEN_ENDED_PATTERNS = [
        re.compile(r"\b(?:explain|describe|tell me about|give me an overview|overview of|summary of|summarize)\b", re.IGNORECASE)
    ]

    def classify(self, query: str) -> Tuple[Intent, float]:
        q = query.lower()
        
        # 1. Comparison
        for pattern in self.COMPARISON_PATTERNS:
            if pattern.search(q):
                return Intent.COMPARISON, 0.95
                
        # 2. Temporal
        for pattern in self.TEMPORAL_PATTERNS:
            if pattern.search(q):
                return Intent.TEMPORAL, 0.90

        # 3. Reasoning / What-if
        for pattern in self.REASONING_PATTERNS:
            if pattern.search(q):
                return Intent.REASONING, 0.85

        # 4. Multi-policy
        for pattern in self.MULTI_POLICY_PATTERNS:
            if pattern.search(q):
                return Intent.MULTI_POLICY, 0.80

        # Open-ended exploratory questions pre-routed to Search before Fact matching
        for pattern in self.OPEN_ENDED_PATTERNS:
            if pattern.search(q):
                return Intent.SEARCH, 0.85

        # 5. Direct Fact
        for pattern in self.FACT_PATTERNS:
            if pattern.search(q):
                return Intent.FACT, 0.90

        # 6. Default to Search / Semantic QA
        if q.startswith(("what is", "how to", "who is", "where is", "can i", "do i", "does ", "is it", "am i", "are employees", "how do", "what are", "when is", "when can")) or q.endswith("?"):
            return Intent.COMPILED_QA, 0.75
            
        return Intent.SEARCH, 0.70
