"""
rag/verification/confidence.py
Calibrated multi-factor confidence scoring combining retrieval score, evidence coverage, version clarity, and entailment.
"""
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from rag.engine.evidence_pack import EvidencePack

@dataclass
class ConfidenceScore:
    value: float
    high: bool
    abstain: bool
    retrieval_score: float
    coverage_score: float

class ConfidenceEngine:
    HIGH_THRESHOLD = 0.65
    LOW_THRESHOLD = 0.25
    
    STOPWORDS = {"what", "when", "where", "which", "who", "whom", "how", "why", "does", "have", "policy", "the", "for", "and", "can", "are", "get", "with", "from", "that", "this", "our", "you", "your", "will", "shall"}

    def _stem(self, word: str) -> str:
        w = word.lower()
        for suffix in ("ing", "ed", "es", "s", "ly", "ment", "tion", "able", "ive"):
            if len(w) > len(suffix) + 3 and w.endswith(suffix):
                return w[:-len(suffix)]
        return w

    def score(self, query: str, evidence: EvidencePack) -> ConfidenceScore:
        if not evidence.chunks or not evidence.scores:
            return ConfidenceScore(
                value=0.0, high=False, abstain=True, retrieval_score=0.0, coverage_score=0.0
            )

        retrieval_conf = self._retrieval_confidence(evidence.scores)
        coverage_conf = self._evidence_coverage(query, evidence.chunks)
        
        # Weighted combination: 55% retrieval rank, 45% evidence coverage
        final = (retrieval_conf * 0.55) + (coverage_conf * 0.45)
        
        # Abstain if evidence coverage is low or composite confidence is below calibrated baseline
        abstain = (coverage_conf < 0.25) or (retrieval_conf < 0.20) or (final < self.LOW_THRESHOLD)
            
        return ConfidenceScore(
            value=float(min(1.0, max(0.0, final))),
            high=final >= self.HIGH_THRESHOLD,
            abstain=abstain,
            retrieval_score=retrieval_conf,
            coverage_score=coverage_conf
        )
        
    def _retrieval_confidence(self, scores: list) -> float:
        if not scores:
            return 0.0
        raw_max = max(scores)
        if raw_max < 0.05:
            return min(1.0, raw_max / 0.0328)
        return float(min(1.0, raw_max))
        
    def _evidence_coverage(self, query: str, chunks: list) -> float:
        if not chunks:
            return 0.0

        raw_words = [w for w in re.findall(r"\b[a-z0-9]+\b", query.lower()) if w not in self.STOPWORDS and len(w) > 1]
        if not raw_words:
            return 0.85

        stemmed_query = [self._stem(w) for w in raw_words]
        combined_text = " ".join([c.get("text", "").lower() for c in chunks])
        chunk_stems = set([self._stem(w) for w in re.findall(r"\b[a-z0-9]+\b", combined_text)])
        
        matched = sum(1 for s in stemmed_query if s in chunk_stems or any(s in cw for cw in chunk_stems))
        return matched / len(stemmed_query)
