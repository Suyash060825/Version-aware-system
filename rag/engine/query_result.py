from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class QueryResult:
    answer: str
    route: str          # "FAST_FACT" | "FAST_QA" | "HYBRID_RAG" | "DEEP_REASONING"
    confidence: float
    citations: List[dict]
    policy_versions: List[dict]
    latency_ms: float
    llm_used: bool
    retrieval_count: int
    reranker_used: bool
    abstained: bool
    model: Optional[str] = None
    usage: dict = field(default_factory=dict)

    @classmethod
    def from_fact(cls, fact, latency_ms: float):
        return cls(
            answer=f"The {fact.predicate.replace('_', ' ')} is {fact.value} {fact.unit}.",
            route="FAST_FACT",
            confidence=fact.confidence,
            citations=[{"chunk_id": fact.source_chunk_id}],
            policy_versions=[{"policy_id": fact.policy_id, "version_id": fact.version_id}],
            latency_ms=latency_ms,
            llm_used=False,
            retrieval_count=0,
            reranker_used=False,
            abstained=False
        )

    @classmethod
    def from_compiled_qa(cls, qa_match: dict, latency_ms: float):
        return cls(
            answer=qa_match["answer"],
            route="FAST_QA",
            confidence=qa_match["confidence"],
            citations=[{"chunk_id": cid} for cid in eval(qa_match.get("source_chunk_ids", "[]"))],
            policy_versions=[],
            latency_ms=latency_ms,
            llm_used=False,
            retrieval_count=1,
            reranker_used=False,
            abstained=False
        )
        
    @classmethod
    def abstained(cls, reason: str, latency_ms: float):
        return cls(
            answer=f"I cannot provide a confident answer based on the available policies. Reason: {reason}",
            route="ABSTAINED",
            confidence=0.0,
            citations=[],
            policy_versions=[],
            latency_ms=latency_ms,
            llm_used=False,
            retrieval_count=0,
            reranker_used=False,
            abstained=True
        )
