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
        r"\b(?:compare|difference|changed|changes|versus|vs|diff|updated from|between v\d+ and v\d+)\b",
        r"\bwhat changed\b",
        r"\bhow is .* different from\b"
    ]
    
    TEMPORAL_PATTERNS = [
        r"\b(?:in 20\d\d|as of|effective date|historical|previous version|prior policy|back in|when was .* enacted|old version)\b",
        r"\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+20\d\d\b",
        r"\bv\d+\b"
    ]
    
    FACT_PATTERNS = [
        r"\b(?:how many|how much|what is the limit|maximum amount|per diem|number of days|working hours|notice period|probation period|gift limit)\b",
        r"\b(?:amount|percentage|threshold|allowance|entitlement)\b"
    ]
    
    REASONING_PATTERNS = [
        r"\b(?:what if|suppose|scenario|if i transfer|how does .* affect|consequences|exception to|is it allowed if)\b",
        r"\b(?:eligible if|can i also|hypothetical)\b"
    ]

    MULTI_POLICY_PATTERNS = [
        r"\b(?:both|and also|across policies|travel and expense.*leave|security.*conduct)\b"
    ]

    def classify(self, query: str) -> Tuple[Intent, float]:
        q = query.lower()
        
        # 1. Comparison
        for pattern in self.COMPARISON_PATTERNS:
            if re.search(pattern, q):
                return Intent.COMPARISON, 0.95
                
        # 2. Temporal
        for pattern in self.TEMPORAL_PATTERNS:
            if re.search(pattern, q):
                return Intent.TEMPORAL, 0.90

        # 3. Reasoning / What-if
        for pattern in self.REASONING_PATTERNS:
            if re.search(pattern, q):
                return Intent.REASONING, 0.85

        # 4. Multi-policy
        for pattern in self.MULTI_POLICY_PATTERNS:
            if re.search(pattern, q):
                return Intent.MULTI_POLICY, 0.80

        # 5. Direct Fact
        for pattern in self.FACT_PATTERNS:
            if re.search(pattern, q):
                return Intent.FACT, 0.90

        # 6. Default to Search / Semantic QA
        if len(q.split()) <= 6 and q.startswith(("what is", "how to", "who is", "where is", "can i")):
            return Intent.COMPILED_QA, 0.75
            
        return Intent.SEARCH, 0.70
