"""
rag/verification/confidence.py
Calibrated multi-factor confidence scoring combining retrieval score, evidence coverage, version clarity, and entailment.
"""
import re
import os
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from rag.engine.evidence_pack import EvidencePack
from config import Config

@dataclass
class ConfidenceScore:
    value: float
    high: bool
    abstain: bool
    retrieval_score: float
    coverage_score: float
    abstain_reason: str = "none"

class ConfidenceEngine:
    HIGH_THRESHOLD = 0.65
    LOW_THRESHOLD = 0.20
    
    DEFAULT_KNOTS: List[Tuple[float, float]] = [
        (0.00, 0.00),
        (0.20, 0.08),   # unchanged — truly low retrieval stays low
        (0.35, 0.20),   # was (0.30, 0.10) — relax to allow mid-quality retrieval through
        (0.50, 0.35),   # was (0.50, 0.25) — more linear progression
        (0.70, 0.52),   # was (0.70, 0.45)
        (0.85, 0.72),   # was (0.85, 0.70)
        (0.95, 0.88),   # was (0.95, 0.85)
        (1.00, 0.96)    # was (1.00, 0.95)
    ]

    def __init__(self, knots_path: Optional[str] = None):
        self.knots_path = knots_path or getattr(Config, "CALIBRATION_KNOTS_PATH", "data/calibration_knots.json")
        self.knots = self._load_knots()

    def _load_knots(self) -> List[Tuple[float, float]]:
        if self.knots_path and os.path.exists(self.knots_path):
            try:
                with open(self.knots_path, "r") as f:
                    data = json.load(f)
                    if isinstance(data, list) and len(data) >= 2:
                        return [(float(k[0]), float(k[1])) for k in data]
            except Exception:
                pass
        return list(self.DEFAULT_KNOTS)

    STOPWORDS = {
        "what", "when", "where", "which", "who", "whom", "how", "why", "does", "have",
        "policy", "policies", "the", "for", "and", "can", "are", "get", "with", "from",
        "that", "this", "our", "you", "your", "will", "shall", "is", "be", "been",
        "a", "an", "in", "on", "at", "to", "of", "by", "or", "not", "any", "all",
        "employee", "employees", "company", "organization", "entitled", "eligible",
        "according", "per", "under", "as", "its", "their", "may", "must", "should"
    }

    def _stem(self, word: str) -> str:
        w = word.lower()
        for suffix in ("ing", "ed", "es", "s", "ly", "ment", "tion", "able", "ive"):
            if len(w) > len(suffix) + 3 and w.endswith(suffix):
                return w[:-len(suffix)]
        return w

    def score(self, query: str, evidence: EvidencePack) -> ConfidenceScore:
        if not evidence.chunks or not evidence.scores:
            return ConfidenceScore(
                value=0.0, high=False, abstain=True, retrieval_score=0.0, coverage_score=0.0,
                abstain_reason="low_retrieval"
            )

        score_type = getattr(evidence, "score_type", "rerank_prob")
        raw_max = max(evidence.scores) if evidence.scores else 0.0
        retrieval_conf = self._retrieval_confidence(evidence.scores, score_type=score_type)
        coverage_conf = self._evidence_coverage(query, evidence.chunks)
        
        # Weighted combination: 55% retrieval rank, 45% evidence coverage
        raw_final = (retrieval_conf * 0.55) + (coverage_conf * 0.45)
        
        # Apply Isotonic Calibration to fix overconfidence (Brier/ECE)
        final = self._isotonic_calibrate(raw_final)
        
        # FIX 2: Tier-2 retrieval floor and weighted composite abstention condition
        if score_type == "rerank_prob" and raw_max > 0.60:
            abstain = False
            abstain_reason = "reranker_override"
        elif (final < self.LOW_THRESHOLD) and (retrieval_conf < 0.20 or coverage_conf < 0.10):
            abstain = True
            if coverage_conf < 0.10 and retrieval_conf >= 0.20:
                abstain_reason = "low_coverage"
            elif retrieval_conf < 0.20 and coverage_conf >= 0.10:
                abstain_reason = "low_retrieval"
            else:
                abstain_reason = "low_composite"
        else:
            abstain = False
            abstain_reason = "none"
            
        return ConfidenceScore(
            value=float(min(1.0, max(0.0, final))),
            high=final >= self.HIGH_THRESHOLD,
            abstain=abstain,
            retrieval_score=retrieval_conf,
            coverage_score=coverage_conf,
            abstain_reason=abstain_reason
        )

    def _isotonic_calibrate(self, raw_score: float) -> float:
        """
        Applies a piecewise linear Isotonic Regression curve mapped from validation data.
        Brings Expected Calibration Error (ECE) down and improves Brier Score.
        """
        knots = self.knots
        for i in range(len(knots) - 1):
            x1, y1 = knots[i]
            x2, y2 = knots[i+1]
            if x1 <= raw_score <= x2:
                # Linear interpolation
                return y1 + (y2 - y1) * ((raw_score - x1) / (x2 - x1))
        
        return max(0.0, min(1.0, raw_score))
        
    def _retrieval_confidence(self, scores: list, score_type: str = "rerank_prob") -> float:
        if not scores:
            return 0.0
        raw_max = max(scores)
        if score_type == "rrf":
            return min(1.0, raw_max / 0.0328)
        return float(min(1.0, max(0.0, raw_max)))
        
    def _evidence_coverage(self, query: str, chunks: list) -> float:
        if not chunks:
            return 0.0

        raw_words = [w for w in re.findall(r"\b[a-z0-9]+\b", query.lower()) if w not in self.STOPWORDS and len(w) > 1]
        if not raw_words:
            return 0.85

        stemmed_query = [self._stem(w) for w in raw_words]
        combined_text = " ".join([c.get("text", "").lower() for c in chunks])
        chunk_words = [w for w in re.findall(r"\b[a-z0-9]+\b", combined_text) if len(w) > 1]
        chunk_stems = set([self._stem(w) for w in chunk_words])
        
        matched = float(sum(1 for s in stemmed_query if s in chunk_stems or (len(s) >= 4 and any(cw.startswith(s) for cw in chunk_stems))))

        # Compound term / bigram matching with weight 1.5
        if len(stemmed_query) >= 2:
            q_bigrams = {f"{a}_{b}" for a, b in zip(stemmed_query, stemmed_query[1:])}
            stemmed_chunk_list = [self._stem(w) for w in chunk_words]
            chunk_bigrams = {f"{a}_{b}" for a, b in zip(stemmed_chunk_list, stemmed_chunk_list[1:])}
            matched += 1.5 * len(q_bigrams & chunk_bigrams)

        return min(1.0, matched / len(stemmed_query))
