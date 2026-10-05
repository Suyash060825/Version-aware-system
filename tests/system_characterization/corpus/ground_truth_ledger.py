"""
tests/system_characterization/corpus/ground_truth_ledger.py
Formal ground-truth ledger for Veritas system characterization.
Stores machine-readable specifications of policies, versions, chunks, facts, QA pairs, and test queries.
Ground truth exists completely independently of system outputs.
"""
import os
import json
import hashlib
from datetime import date, datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Set, Tuple

def date_serializer(obj):
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


@dataclass
class ChunkLedgerEntry:
    chunk_id: str
    policy_id: int
    version_id: int
    version_label: str
    section_path: str
    page: int
    paragraph_num: int
    text: str
    text_hash: str
    embedding_hash: str
    char_count: int
    effective_start: str  # YYYY-MM-DD
    effective_end: Optional[str]  # YYYY-MM-DD or None (open-ended/active)
    department_id: Optional[int]
    department_name: str
    confidentiality: str  # public, internal, confidential, restricted
    allowed_roles: List[str]
    parent_version_id: Optional[int]
    supersedes_version_id: Optional[int]
    mutation_type: str  # MUT-A through MUT-R, or INITIAL
    expected_embedding_action: str  # "NEW_EMBED", "REUSE_HASH", "TOMBSTONE"
    expected_index_status: str  # "INDEXED", "ARCHIVED", "DELETED"
    is_active_version: bool


@dataclass
class FactLedgerEntry:
    fact_id: str
    policy_id: int
    version_id: int
    subject: str
    predicate: str
    value: str
    unit: Optional[str]
    scope: str
    source_chunk_id: str
    confidence: float


@dataclass
class CanonicalQALedgerEntry:
    qa_id: str
    policy_id: int
    version_id: int
    question: str
    question_hash: str
    target_answer: str
    source_chunk_ids: List[str]
    quality_score: float
    status: str


@dataclass
class VersionLedgerEntry:
    version_id: int
    policy_id: int
    policy_code: str
    version_num: float
    version_label: str
    effective_start: str
    effective_end: Optional[str]
    is_active: bool
    status: str
    confidentiality: str
    department_id: Optional[int]
    mutation_type: str
    change_summary: str
    chunk_ids: List[str]
    fact_ids: List[str]
    qa_ids: List[str]


@dataclass
class PolicyLedgerEntry:
    policy_id: int
    policy_code: str
    title: str
    category: str
    department_id: Optional[int]
    department_name: str
    confidentiality: str
    priority: str
    is_mandatory: bool
    versions: List[VersionLedgerEntry] = field(default_factory=list)


@dataclass
class QueryGroundTruth:
    query_id: str
    user_id: str
    user_role: str
    user_department: str
    user_clearance: str
    query_text: str
    expected_authorization: bool
    expected_route: str  # FAST_PATH_FACT, FAST_PATH_COMPILED_QA, HYBRID_RAG, TEMPORAL_COMPARISON, COMPLEX_REASONING, ABSTAIN, REFUSAL
    query_category: str  # A through T
    difficulty: str  # easy, medium, hard, adversarial
    query_date: Optional[str] = None  # YYYY-MM-DD or None (current)
    intended_policy_id: Optional[int] = None
    intended_policy_title: Optional[str] = None
    intended_version_num: Optional[str] = None
    expected_answer_contains: List[str] = field(default_factory=list)
    expected_answer_exact: Optional[str] = None
    expected_evidence_chunks: List[str] = field(default_factory=list)
    expected_citations: List[Dict[str, Any]] = field(default_factory=list)
    expected_abstention: bool = False
    is_adversarial: bool = False
    is_temporal: bool = False
    is_ambiguous: bool = False
    notes: str = ""


class GroundTruthLedger:
    def __init__(self):
        self.policies: Dict[int, PolicyLedgerEntry] = {}
        self.versions: Dict[int, VersionLedgerEntry] = {}
        self.chunks: Dict[str, ChunkLedgerEntry] = {}
        self.facts: Dict[str, FactLedgerEntry] = {}
        self.canonical_qas: Dict[str, CanonicalQALedgerEntry] = {}
        self.queries: Dict[str, QueryGroundTruth] = {}

    def add_policy(self, policy: PolicyLedgerEntry):
        self.policies[policy.policy_id] = policy

    def add_version(self, version: VersionLedgerEntry):
        self.versions[version.version_id] = version

    def add_chunk(self, chunk: ChunkLedgerEntry):
        self.chunks[chunk.chunk_id] = chunk

    def add_fact(self, fact: FactLedgerEntry):
        self.facts[fact.fact_id] = fact

    def add_canonical_qa(self, qa: CanonicalQALedgerEntry):
        self.canonical_qas[qa.qa_id] = qa

    def add_query(self, query: QueryGroundTruth):
        self.queries[query.query_id] = query

    def save(self, filepath: str):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        data = {
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "policy_count": len(self.policies),
                "version_count": len(self.versions),
                "chunk_count": len(self.chunks),
                "fact_count": len(self.facts),
                "canonical_qa_count": len(self.canonical_qas),
                "query_count": len(self.queries),
            },
            "policies": [asdict(p) for p in self.policies.values()],
            "versions": [asdict(v) for v in self.versions.values()],
            "chunks": [asdict(c) for c in self.chunks.values()],
            "facts": [asdict(f) for f in self.facts.values()],
            "canonical_qas": [asdict(q) for q in self.canonical_qas.values()],
            "queries": [asdict(qry) for qry in self.queries.values()],
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=date_serializer)

    @classmethod
    def load(cls, filepath: str) -> "GroundTruthLedger":
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        ledger = cls()
        for p_data in data.get("policies", []):
            versions = [VersionLedgerEntry(**v) for v in p_data.pop("versions", [])]
            p = PolicyLedgerEntry(versions=versions, **p_data)
            ledger.add_policy(p)
        for v_data in data.get("versions", []):
            ledger.add_version(VersionLedgerEntry(**v_data))
        for c_data in data.get("chunks", []):
            ledger.add_chunk(ChunkLedgerEntry(**c_data))
        for f_data in data.get("facts", []):
            ledger.add_fact(FactLedgerEntry(**f_data))
        for q_data in data.get("canonical_qas", []):
            ledger.add_canonical_qa(CanonicalQALedgerEntry(**q_data))
        for qry_data in data.get("queries", []):
            ledger.add_query(QueryGroundTruth(**qry_data))
        return ledger
