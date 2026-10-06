"""
tests/expanded_characterization/ledger.py
Data structures and schema definitions for the Veritas Expanded Characterization Benchmark (10,000+ chunks, 600+ policies, 7,000+ queries).
"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import json
import hashlib
from datetime import datetime

@dataclass
class PolicyMetadata:
    policy_id: str
    title: str
    department_id: int
    department_name: str
    department_code: str
    confidentiality: str  # "public", "internal", "confidential", "restricted"
    predicate: str
    unit: str
    structure_type: str  # "short", "medium", "long", "table", "nested"
    domain_description: str
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class PolicyVersion:
    version_id: str
    policy_id: str
    version_number: int
    version_tag: str  # "v1.0", "v2.0", etc.
    effective_from: str  # ISO timestamp YYYY-MM-DDTHH:MM:SS
    effective_to: Optional[str]  # ISO timestamp or None if active
    is_active: bool
    is_revoked: bool
    supersedes_version_id: Optional[str]
    change_type: str  # "initial", "minor_amendment", "major_revision", "revocation"
    change_summary: str
    predicate_value: Any
    full_text: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class PolicyChunk:
    chunk_id: str
    policy_id: str
    version_id: str
    chunk_index: int
    section_title: str
    text: str
    sha256_hash: str
    token_count_est: int
    effective_from: str
    effective_to: Optional[str]
    department_id: int
    confidentiality: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class PolicyFact:
    fact_id: str
    policy_id: str
    version_id: str
    chunk_id: str
    predicate: str
    value: Any
    unit: str
    effective_from: str
    effective_to: Optional[str]
    department_id: int
    confidentiality: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class CanonicalQAPair:
    qa_id: str
    policy_id: str
    version_id: str
    query_text: str
    canonical_answer: str
    evidence_chunk_ids: List[str]
    predicate: str
    effective_from: str
    effective_to: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class QueryGroundTruth:
    query_id: str
    category: str  # "A" through "P"
    category_name: str
    difficulty: str  # "easy", "medium", "hard", "adversarial"
    split: str  # "train", "dev", "test"
    query_text: str
    query_timestamp: str  # ISO timestamp
    user_id: str
    user_role: str
    user_department_id: int
    user_clearance: str
    expected_authorization: bool
    expected_temporal_validity: bool
    target_policy_ids: List[str]
    target_version_ids: List[str]
    target_chunk_ids: List[str]
    target_fact_ids: List[str]
    expected_answer: str
    expected_route: str  # "TIER_0_FACT", "TIER_1_SEMANTIC", "TIER_2_HYBRID", "REFUSAL"
    expected_abstention: bool
    refusal_reason: Optional[str] = None
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class ExpandedGroundTruthLedger:
    metadata: Dict[str, Any] = field(default_factory=dict)
    policies: List[PolicyMetadata] = field(default_factory=list)
    versions: List[PolicyVersion] = field(default_factory=list)
    chunks: List[PolicyChunk] = field(default_factory=list)
    facts: List[PolicyFact] = field(default_factory=list)
    canonical_qas: List[CanonicalQAPair] = field(default_factory=list)
    queries: List[QueryGroundTruth] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata": self.metadata,
            "policies": [p.to_dict() for p in self.policies],
            "versions": [v.to_dict() for v in self.versions],
            "chunks": [c.to_dict() for c in self.chunks],
            "facts": [f.to_dict() for f in self.facts],
            "canonical_qas": [qa.to_dict() for qa in self.canonical_qas],
            "queries": [q.to_dict() for q in self.queries]
        }

    def save_json(self, file_path: str):
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
