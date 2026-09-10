"""
rag/router/complexity_classifier.py
Classifies query complexity levels (L0 to L4) to enforce strict computation budgets.
"""
from enum import IntEnum
from typing import Tuple
from rag.router.intent_classifier import Intent, IntentClassifier

class ComplexityLevel(IntEnum):
    LEVEL_0_FACT = 0         # Structured deterministic fact lookup (<1ms, no vector/LLM)
    LEVEL_1_COMPILED_QA = 1  # Precomputed canonical QA match (<5ms, no LLM)
    LEVEL_2_RETRIEVAL = 2    # Hybrid dense+sparse retrieval + rerank (<50ms)
    LEVEL_3_COMPARISON = 3   # Version diff / temporal resolution (deterministic diff / LLM summary)
    LEVEL_4_REASONING = 4    # Complex multi-policy reasoning / what-if (Local small LLM required)

class ComplexityClassifier:
    def __init__(self):
        self.intent_classifier = IntentClassifier()

    def classify(self, query: str, intent: Intent = None) -> Tuple[ComplexityLevel, str]:
        if intent is None:
            intent, _ = self.intent_classifier.classify(query)

        if intent == Intent.FACT:
            return ComplexityLevel.LEVEL_0_FACT, "FAST_PATH_FACT"
        elif intent == Intent.COMPILED_QA:
            return ComplexityLevel.LEVEL_1_COMPILED_QA, "FAST_PATH_COMPILED_QA"
        elif intent == Intent.SEARCH:
            return ComplexityLevel.LEVEL_2_RETRIEVAL, "HYBRID_RAG"
        elif intent in (Intent.COMPARISON, Intent.TEMPORAL):
            return ComplexityLevel.LEVEL_3_COMPARISON, "TEMPORAL_COMPARISON"
        elif intent in (Intent.REASONING, Intent.MULTI_POLICY):
            return ComplexityLevel.LEVEL_4_REASONING, "COMPLEX_REASONING"
        else:
            return ComplexityLevel.LEVEL_2_RETRIEVAL, "HYBRID_RAG"
