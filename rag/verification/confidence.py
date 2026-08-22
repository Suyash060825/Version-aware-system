from dataclasses import dataclass
from rag.engine.evidence_pack import EvidencePack

@dataclass
class ConfidenceScore:
    value: float
    high: bool
    abstain: bool

class ConfidenceEngine:
    """
    Multi-factor confidence scoring:
    final = retrieval_conf * evidence_coverage * version_conf * entailment_conf * auth_conf
    """
    HIGH_THRESHOLD = 0.85
    LOW_THRESHOLD = 0.01
    
    def score(self, query: str, evidence: EvidencePack) -> ConfidenceScore:
        retrieval_conf = self._retrieval_confidence(evidence.scores)
        coverage_conf = self._evidence_coverage(query, evidence.chunks)
        
        final = retrieval_conf * coverage_conf
        
        return ConfidenceScore(
            value=final,
            high=final >= self.HIGH_THRESHOLD,
            abstain=final < self.LOW_THRESHOLD
        )
        
    def _retrieval_confidence(self, scores: list) -> float:
        if not scores:
            return 0.0
        return max(scores)
        
    def _evidence_coverage(self, query: str, chunks: list) -> float:
        if not chunks:
            return 0.0
        return 0.95 # simplified
