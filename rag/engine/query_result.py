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
    retrieved_chunk_ids: List[str] = field(default_factory=list)
    model: Optional[str] = None
    usage: dict = field(default_factory=dict)
    abstain_reason: str = "none"
    nli_verdict: str = "none"
    nli_entailment_score: float = 0.0
    nli_contradiction_score: float = 0.0
    llm_token_count: int = 0
    llm_time_ms: float = 0.0

    @property
    def cache_hit(self) -> bool:
        return self.route in ("CACHE_HIT", "L1_CACHE", "L2_CACHE")

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
        import json
        source_ids = qa_match.get("source_chunk_ids", [])
        if isinstance(source_ids, str):
            try:
                chunk_ids = json.loads(source_ids)
            except (json.JSONDecodeError, TypeError):
                chunk_ids = []
        elif isinstance(source_ids, (list, tuple)):
            chunk_ids = source_ids
        else:
            chunk_ids = []

        return cls(
            answer=qa_match["answer"],
            route="FAST_QA",
            confidence=qa_match["confidence"],
            citations=[{"chunk_id": cid} for cid in chunk_ids],
            policy_versions=[],
            latency_ms=latency_ms,
            llm_used=False,
            retrieval_count=1,
            reranker_used=False,
            abstained=False
        )
        
    @classmethod
    def abstained(cls, reason: str, latency_ms: float, abstain_reason: str = "low_composite", usage: Optional[dict] = None):
        if reason.startswith("I cannot") or reason.startswith("I could not"):
            ans = reason
        else:
            ans = f"I cannot provide a confident answer based on the available policies. Reason: {reason}"
        return cls(
            answer=ans,
            route="ABSTAINED",
            confidence=0.0,
            citations=[],
            policy_versions=[],
            latency_ms=latency_ms,
            llm_used=False,
            retrieval_count=0,
            reranker_used=False,
            abstained=True,
            abstain_reason=abstain_reason,
            usage=usage or {}
        )
