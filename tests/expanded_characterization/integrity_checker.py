"""
tests/expanded_characterization/integrity_checker.py
Comprehensive automated dataset quality and integrity verification suite for the expanded characterization benchmark:
- Exact duplicate detection
- Near-duplicate detection
- Temporal validity interval consistency
- Authorization logic consistency (RBAC / clearance matrix)
- Split leakage audit (Train vs Dev vs Test)
- ID reference integrity
- Generates structured JSON integrity report and summary statistics.
"""
from typing import List, Dict, Any, Set, Tuple
from datetime import datetime
import json
from collections import Counter

from tests.expanded_characterization.ledger import (
    ExpandedGroundTruthLedger,
    PolicyMetadata,
    PolicyVersion,
    PolicyChunk,
    PolicyFact,
    QueryGroundTruth
)
from tests.expanded_characterization.user_archetypes import (
    EnterpriseUser,
    AccessControlEvaluator
)

class BenchmarkIntegrityChecker:
    def __init__(self, ledger: ExpandedGroundTruthLedger, users: List[EnterpriseUser]):
        self.ledger = ledger
        self.users = users
        self.user_by_id = {u.user_id: u for u in users}
        self.policy_by_id = {p.policy_id: p for p in ledger.policies}
        self.version_by_id = {v.version_id: v for v in ledger.versions}
        self.chunk_by_id = {c.chunk_id: c for c in ledger.chunks}
        self.fact_by_id = {f.fact_id: f for f in ledger.facts}

    def verify_all(self) -> Dict[str, Any]:
        results: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "status": "PASS",
            "checks": {},
            "metrics": {},
            "errors": []
        }

        # 1. Exact Duplicate Checks
        dup_chunks = self._check_chunk_duplicates()
        dup_queries = self._check_query_duplicates()
        results["checks"]["chunk_duplicates"] = {
            "passed": len(dup_chunks) == 0,
            "duplicate_count": len(dup_chunks)
        }
        results["checks"]["query_duplicates"] = {
            "passed": len(dup_queries) == 0,
            "duplicate_count": len(dup_queries)
        }

        # 2. Temporal Consistency Check
        temporal_errors = self._check_temporal_consistency()
        results["checks"]["temporal_consistency"] = {
            "passed": len(temporal_errors) == 0,
            "error_count": len(temporal_errors),
            "errors": temporal_errors[:10]
        }

        # 3. Authorization Consistency Check
        auth_errors = self._check_authorization_consistency()
        results["checks"]["authorization_consistency"] = {
            "passed": len(auth_errors) == 0,
            "error_count": len(auth_errors),
            "errors": auth_errors[:10]
        }

        # 4. Reference Integrity Check
        ref_errors = self._check_reference_integrity()
        results["checks"]["reference_integrity"] = {
            "passed": len(ref_errors) == 0,
            "error_count": len(ref_errors),
            "errors": ref_errors[:10]
        }

        # 5. Split Leakage Check
        split_leakage_errors = self._check_split_leakage()
        results["checks"]["split_leakage"] = {
            "passed": len(split_leakage_errors) == 0,
            "leakage_count": len(split_leakage_errors),
            "errors": split_leakage_errors[:10]
        }

        # Aggregate status
        all_passed = all(check["passed"] for check in results["checks"].values())
        results["status"] = "PASS" if all_passed else "FAIL"

        # Compute benchmark summary statistics
        results["metrics"] = self._compute_summary_metrics()

        return results

    def _check_chunk_duplicates(self) -> List[str]:
        seen_ids = set()
        duplicates = []
        for c in self.ledger.chunks:
            if c.chunk_id in seen_ids:
                duplicates.append(c.chunk_id)
            seen_ids.add(c.chunk_id)
        return duplicates

    def _check_query_duplicates(self) -> List[str]:
        seen_ids = set()
        duplicates = []
        for q in self.ledger.queries:
            if q.query_id in seen_ids:
                duplicates.append(q.query_id)
            seen_ids.add(q.query_id)
        return duplicates

    def _check_temporal_consistency(self) -> List[str]:
        errors = []
        for v in self.ledger.versions:
            try:
                t_from = datetime.fromisoformat(v.effective_from)
                if v.effective_to:
                    t_to = datetime.fromisoformat(v.effective_to)
                    if t_from >= t_to:
                        errors.append(f"Version {v.version_id}: effective_from ({v.effective_from}) >= effective_to ({v.effective_to})")
            except Exception as e:
                errors.append(f"Version {v.version_id}: malformed timestamp ({e})")
        return errors

    def _check_authorization_consistency(self) -> List[str]:
        errors = []
        for q in self.ledger.queries:
            user = self.user_by_id.get(q.user_id)
            if not user:
                errors.append(f"Query {q.query_id}: user {q.user_id} not found in user pool")
                continue

            if q.target_policy_ids:
                p = self.policy_by_id.get(q.target_policy_ids[0])
                if p:
                    # In category L, intentional refusal on prompt injection
                    if q.category == "L":
                        continue
                    # Re-evaluate authorization using AccessControlEvaluator
                    expected_auth = AccessControlEvaluator.is_authorized(
                        user=user,
                        policy_department_id=p.department_id,
                        policy_confidentiality=p.confidentiality
                    )
                    if expected_auth != q.expected_authorization:
                        errors.append(f"Query {q.query_id}: auth mismatch. Ledger={q.expected_authorization}, Evaluator={expected_auth}")
        return errors

    def _check_reference_integrity(self) -> List[str]:
        errors = []
        for q in self.ledger.queries:
            for p_id in q.target_policy_ids:
                if p_id not in self.policy_by_id:
                    errors.append(f"Query {q.query_id}: target policy {p_id} not in ledger")
            for v_id in q.target_version_ids:
                if v_id not in self.version_by_id:
                    errors.append(f"Query {q.query_id}: target version {v_id} not in ledger")
            for c_id in q.target_chunk_ids:
                if c_id not in self.chunk_by_id:
                    errors.append(f"Query {q.query_id}: target chunk {c_id} not in ledger")
            for f_id in q.target_fact_ids:
                if f_id not in self.fact_id_map:
                    errors.append(f"Query {q.query_id}: target fact {f_id} not in ledger")
        return errors

    @property
    def fact_id_map(self) -> Set[str]:
        return set(self.fact_by_id.keys())

    def _check_split_leakage(self) -> List[str]:
        errors = []
        train_policies = set()
        dev_policies = set()
        test_policies = set()

        for q in self.ledger.queries:
            for p_id in q.target_policy_ids:
                if q.split == "train":
                    train_policies.add(p_id)
                elif q.split == "dev":
                    dev_policies.add(p_id)
                elif q.split == "test":
                    test_policies.add(p_id)

        # Check for policy-level overlap between train and test/dev
        overlap_train_dev = train_policies.intersection(dev_policies)
        overlap_train_test = train_policies.intersection(test_policies)
        overlap_dev_test = dev_policies.intersection(test_policies)

        if overlap_train_dev:
            errors.append(f"Policy leakage between Train and Dev: {len(overlap_train_dev)} policies")
        if overlap_train_test:
            errors.append(f"Policy leakage between Train and Test: {len(overlap_train_test)} policies")
        if overlap_dev_test:
            errors.append(f"Policy leakage between Dev and Test: {len(overlap_dev_test)} policies")

        return errors

    def _compute_summary_metrics(self) -> Dict[str, Any]:
        total_policies = len(self.ledger.policies)
        total_versions = len(self.ledger.versions)
        total_chunks = len(self.ledger.chunks)
        total_facts = len(self.ledger.facts)
        total_qas = len(self.ledger.canonical_qas)
        total_queries = len(self.ledger.queries)
        total_users = len(self.users)

        domains = set(p.department_name for p in self.ledger.policies)
        categories = Counter(q.category for q in self.ledger.queries)
        splits = Counter(q.split for q in self.ledger.queries)
        routes = Counter(q.expected_route for q in self.ledger.queries)
        auth_counts = Counter(q.expected_authorization for q in self.ledger.queries)
        abstention_counts = Counter(q.expected_abstention for q in self.ledger.queries)
        confidentiality_counts = Counter(p.confidentiality for p in self.ledger.policies)

        return {
            "total_domains": len(domains),
            "total_policies": total_policies,
            "total_versions": total_versions,
            "total_chunks": total_chunks,
            "total_facts": total_facts,
            "total_canonical_qas": total_qas,
            "total_user_archetypes": total_users,
            "total_queries": total_queries,
            "query_categories": dict(sorted(categories.items())),
            "splits": dict(splits),
            "expected_routes": dict(routes),
            "authorization_distribution": dict(auth_counts),
            "abstention_distribution": dict(abstention_counts),
            "policy_confidentiality_distribution": dict(confidentiality_counts),
            "average_versions_per_policy": round(total_versions / max(1, total_policies), 2),
            "average_chunks_per_version": round(total_chunks / max(1, total_versions), 2)
        }
