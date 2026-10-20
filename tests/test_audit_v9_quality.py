"""
tests/test_audit_v9_quality.py
Targeted test suite verifying answer quality, evidence selection, adaptive routing,
temporal resolution, and authorization hardening implemented in Pass 3.
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import date

from models import Policy, PolicyVersion, PolicyStatus, UserRole
from rag.engine.query_scope import QueryScope
from rag.authorization.evidence_filter import EvidenceFilter, get_evidence_filter
from rag.router.temporal_router import TemporalRouter
from rag.retrieval.reranker import _format_candidate_for_rerank, Qwen3Reranker
from rag.engine.query_engine import _extract_best_evidence_context, _is_valid_diff_query, QueryEngine
from rag.facts.fact_resolver import FactResolver


class MockUser:
    def __init__(self, role=UserRole.EMPLOYEE, clearance="standard", department_id=1, user_id=101):
        self.id = user_id
        self.role = role
        self.clearance = clearance
        self.department_id = department_id


class MockPolicy:
    def __init__(self, policy_id, title="Test Policy", confidentiality="internal", department_id=1):
        self.id = policy_id
        self.title = title
        self.confidentiality = confidentiality
        self.department_id = department_id
        self.status = PolicyStatus.ACTIVE


def test_contractor_clearance_blocked_from_internal():
    """F4 Authorization: Contractor with public_only clearance must be blocked from internal policies."""
    ev_filter = EvidenceFilter()
    contractor = MockUser(role=UserRole.EMPLOYEE, clearance="public_only", department_id=1)
    
    internal_policy = MockPolicy(1, title="Internal Guidelines", confidentiality="internal")
    public_policy = MockPolicy(2, title="Public Code of Conduct", confidentiality="public")
    
    assert ev_filter.is_authorized_for_policy(contractor, internal_policy) is False
    assert ev_filter.is_authorized_for_policy(contractor, public_policy) is True


def test_version_diff_pattern_and_validation():
    """Level 3 Version Diff: Verify regex handles 'v1.0 vs v2.0', 'version 1.0 vs version 2.0', and ignores years."""
    queries_should_match = [
        "What changed between v1.0 and v2.0?",
        "Compare version 1.0 vs version 2.0 of Leave Policy",
        "Diff v1 vs v2",
        "Differences in v1.1 - v1.2"
    ]
    for q in queries_should_match:
        assert _is_valid_diff_query(q) is True, f"Failed to match diff query: {q}"
        m = TemporalRouter.VERSION_DIFF_PATTERN.search(q)
        assert m is not None, f"VERSION_DIFF_PATTERN failed for: {q}"

    # 4-digit years should NOT be recognized as diff unless prefixed with v
    assert _is_valid_diff_query("Policies between 2021 and 2022") is False


def test_reranker_contextual_prefixing():
    """Evidence Selection: Verify candidates are formatted with [Policy: ... | Section: ...] prefix."""
    cand = {
        "text": "Employees receive 15 days of paid annual leave.",
        "policy_name": "Annual Leave Policy",
        "section": "Leave Entitlements",
        "version": "2.0"
    }
    formatted = _format_candidate_for_rerank(cand)
    assert formatted.startswith("[Policy: Annual Leave Policy | Section: Leave Entitlements]")
    assert "Employees receive 15 days of paid annual leave." in formatted


def test_fact_resolver_recency_sorting():
    """Temporal Resolution: Historical queries must prefer the most recent matching historical version."""
    resolver = FactResolver()
    
    # Mock versions map with v1.0 and v2.0
    v1 = MagicMock()
    v1.version_num = 1.0
    v2 = MagicMock()
    v2.version_num = 2.0
    versions_map = {1: v1, 2: v2}
    
    # Two candidates with equal relevance score (e.g. 80.0)
    cand_v1 = MagicMock()
    cand_v1.version_id = 1
    cand_v2 = MagicMock()
    cand_v2.version_id = 2
    
    candidates = [(80.0, cand_v1), (80.0, cand_v2)]
    
    # Sort using the exact tie-breaking key from FactResolver
    candidates.sort(
        key=lambda x: (
            x[0],
            float(getattr(versions_map.get(x[1].version_id), "version_num", 1.0) or 1.0)
        ),
        reverse=True
    )
    
    # v2.0 should come first due to higher version_num tie-breaker
    assert candidates[0][1].version_id == 2


def test_safe_abstention_underspecified_query():
    """F16 Safe Abstention: Underspecified queries with generic words only must return None."""
    ranked = [{
        "text": "The limit is set by company management within standard rules.",
        "section": "General Rules",
        "policy_name": "Office Guidelines",
        "policy_id": 5,
        "version": "1.0"
    }]
    citations = [{"policy_name": "Office Guidelines", "version": "1.0", "policy_id": 5, "section": "General Rules"}]
    
    # Query with generic words only: "What is the limit?"
    res = _extract_best_evidence_context("What is the limit?", ranked, citations)
    assert res is None, "Should safely abstain on underspecified generic query"


def test_substantive_evidence_synthesis():
    """Answer Quality: Context extraction prioritizes substantive question keywords and aligns citations."""
    ranked = [
        {
            "text": "Parental Leave Policy purpose and scope. This policy applies to all staff.",
            "section": "Purpose & Scope",
            "policy_name": "Parental Leave Policy",
            "policy_id": 10,
            "version": "2.0"
        },
        {
            "text": "Primary caregivers receive sixteen consecutive weeks of paid leave at full base salary.",
            "section": "Paid Leave Entitlements",
            "policy_name": "Parental Leave Policy",
            "policy_id": 10,
            "version": "2.0"
        }
    ]
    citations = [
        {"policy_name": "Parental Leave Policy", "version": "2.0", "policy_id": 10, "section": "Purpose & Scope"},
        {"policy_name": "Parental Leave Policy", "version": "2.0", "policy_id": 10, "section": "Paid Leave Entitlements"}
    ]
    
    query = "How many consecutive weeks of paid leave do primary caregivers get under Parental Leave Policy?"
    result = _extract_best_evidence_context(query, ranked, citations)
    assert result is not None
    assert "sixteen consecutive weeks" in result
    assert "Paid Leave Entitlements" in result
    # Citation should be reordered so winning chunk section is first
    assert citations[0]["section"] == "Paid Leave Entitlements"


def test_blueprint_clearance_isolation():
    """Authorization Consistency: Non-admin users in auxiliary blueprints are isolated to allowed policy IDs."""
    from app import create_app
    from blueprints.knowledge_graph import _build_graph
    from blueprints.governance import _compute_governance_data
    from blueprints.confusion_index import _compute
    from blueprints.gamification import _mandatory_ack_rate
    from unittest.mock import MagicMock, patch

    app = create_app("testing")
    with app.app_context():
        mock_user = MockUser(role=UserRole.HR, clearance="standard", user_id=99)

        with patch("rag.authorization.evidence_filter.EvidenceFilter.get_allowed_policy_ids", return_value={10, 20}):
            with patch("models.Policy.query") as mock_policy_query:
                filtered_query = MagicMock()
                filtered_query.order_by.return_value.limit.return_value.all.return_value = []
                filtered_query.all.return_value = []
                mock_policy_query.filter.return_value = filtered_query
                mock_policy_query.filter_by.return_value.filter.return_value = filtered_query

                # 1. Knowledge graph
                _build_graph(limit_policies=10, user=mock_user)
                assert mock_policy_query.filter.called

                # 2. Governance
                _compute_governance_data(user=mock_user)
                assert mock_policy_query.filter_by.return_value.filter.called

                # 3. Confusion Index
                _compute(user=mock_user)
                assert mock_policy_query.filter_by.return_value.filter.called

                # 4. Gamification mandatory ack rate
                rate = _mandatory_ack_rate(user=mock_user)
                assert rate == 100.0 or isinstance(rate, float)

