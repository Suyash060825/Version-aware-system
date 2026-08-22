from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class EvidencePack:
    query: str
    route: str          # "FACT" | "QA" | "RAG" | "REASONING"
    policy_ids: List[int] = field(default_factory=list)
    version_ids: List[int] = field(default_factory=list)
    facts: List[dict] = field(default_factory=list)
    chunks: List[dict] = field(default_factory=list)
    scores: List[float] = field(default_factory=list)
    authorization: dict = field(default_factory=dict)
    confidence: float = 0.0
