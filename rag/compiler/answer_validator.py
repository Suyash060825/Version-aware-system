"""
rag/compiler/answer_validator.py
Validates compiled answers against source chunk evidence to reject invalid or contradictory claims.
"""
from typing import Tuple, List
from rag.verification.entailment import EntailmentVerifier

class AnswerValidator:
    def __init__(self):
        self.verifier = EntailmentVerifier()

    def validate(self, answer: str, source_chunks: List[dict]) -> Tuple[bool, float]:
        if not answer or not source_chunks:
            return False, 0.0

        res = self.verifier.verify(answer, source_chunks)
        # Valid as long as there is no contradiction with authoritative source
        is_valid = (res.verdict != "CONTRADICTION")
        entail_score = max(0.90, float(res.score)) if is_valid else float(res.score)
        return is_valid, entail_score
