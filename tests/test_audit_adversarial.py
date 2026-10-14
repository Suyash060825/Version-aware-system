"""
tests/test_audit_adversarial.py
Independent Audit Test Suite for Phase 5 (Temporal & Authorization) and Phase 6 (Grounding & Abstention).
Executes all mandated edge cases without modifying production code.
"""
import pytest
import os
import json
import time
from datetime import date, timedelta
from app import create_app
from models import (db, Policy, PolicyVersion, PolicyChunkV2, PolicyFact, 
                    CanonicalQuestion, CompiledAnswer, User, UserRole, 
                    PolicyStatus, ConfidentialityLevel, Department)
from rag.engine.query_engine import get_query_engine, QueryEngine
from rag.versions.resolver import VersionResolver
from rag.authorization.evidence_filter import EvidenceFilter
from rag.engine.query_scope import QueryScope
from rag.cache.semantic_cache import get_cache
from rag.verification.entailment import EntailmentVerifier

@pytest.fixture(scope="module")
def audit_app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        # Seed test departments
        dept_hr = Department(id=1, name="Human Resources", code="HR")
        dept_eng = Department(id=2, name="Engineering", code="ENG")
        dept_sec = Department(id=3, name="IT & Security", code="SEC")
        db.session.add_all([dept_hr, dept_eng, dept_sec])

        # Seed test users
        u_admin = User(id=1, name="Admin User", email="admin@audit.com", password_hash="hash", role=UserRole.ADMIN, department_id=3)
        u_hr = User(id=2, name="HR User", email="hr@audit.com", password_hash="hash", role=UserRole.HR, department_id=1)
        u_eng = User(id=3, name="Eng User", email="eng@audit.com", password_hash="hash", role=UserRole.EMPLOYEE, department_id=2)
        u_contractor = User(id=4, name="Contractor", email="ext@audit.com", password_hash="hash", role=UserRole.EMPLOYEE, department_id=2)
        db.session.add_all([u_admin, u_hr, u_eng, u_contractor])

        # Policy 1: Remote Work Policy (v1: 2022-01-01 to 2023-12-31, v2: 2024-01-01 onwards)
        p_remote = Policy(id=1, policy_id="POL-REMOTE", title="Remote Work Policy", author_id=2, department_id=1,
                          status=PolicyStatus.ACTIVE, confidentiality=ConfidentialityLevel.INTERNAL)
        db.session.add(p_remote)
        db.session.flush()

        v1_remote = PolicyVersion(
            id=1, policy_id=1, version_num=1.0, version_label="v1.0",
            content="Employees may work remotely 1 day per week. Mandatory 4 days in office. Home office equipment is not provided.",
            is_active=False, status="superseded", created_by_id=2,
            effective_date=date(2022, 1, 1)
        )
        v2_remote = PolicyVersion(
            id=2, policy_id=1, version_num=2.0, version_label="v2.0",
            content="Employees may work remotely up to 3 days per week. Minimum 2 in-office days required. Standard laptop provided. Internet allowance is Rs 500 per month.",
            is_active=True, status="active", created_by_id=2,
            effective_date=date(2024, 1, 1)
        )
        db.session.add_all([v1_remote, v2_remote])

        # Policy 2: Confidential Security Control (Restricted to IT/Admin)
        p_sec = Policy(id=2, policy_id="POL-SEC", title="Cybersecurity Incident Plan", author_id=1, department_id=3,
                       status=PolicyStatus.ACTIVE, confidentiality=ConfidentialityLevel.RESTRICTED)
        db.session.add(p_sec)
        db.session.flush()

        v1_sec = PolicyVersion(
            id=3, policy_id=2, version_num=1.0, version_label="v1.0",
            content="Severity 1 incident protocol: notify SOC within 15 minutes. Key rotation keyvault master token: ALPHA-99-SECRET.",
            is_active=True, status="approved", created_by_id=1,
            effective_date=date(2023, 1, 1)
        )
        db.session.add(v1_sec)

        # Policy 3: Expired Special Project Policy (Validity: 2021-01-01 to 2021-12-31)
        p_exp = Policy(id=3, policy_id="POL-EXP", title="COVID-19 Emergency Stipend", author_id=2, department_id=1,
                       status=PolicyStatus.ARCHIVED, confidentiality=ConfidentialityLevel.INTERNAL, expiry_date=date(2021, 12, 31))
        db.session.add(p_exp)
        db.session.flush()

        v1_exp = PolicyVersion(
            id=4, policy_id=3, version_num=1.0, version_label="v1.0",
            content="COVID-19 emergency stipend provides Rs. 10,000 one-time allowance for health supplies. Expired Dec 2021.",
            is_active=False, status="archived", created_by_id=2,
            effective_date=date(2021, 1, 1)
        )
        db.session.add(v1_exp)

        # Policy 4: Future Effective Policy (Effective from 2028-01-01)
        p_future = Policy(id=4, policy_id="POL-FUT", title="Autonomous AI Agent Governance", author_id=1, department_id=2,
                          status=PolicyStatus.DRAFT, confidentiality=ConfidentialityLevel.INTERNAL)
        db.session.add(p_future)
        db.session.flush()

        v1_fut = PolicyVersion(
            id=5, policy_id=4, version_num=1.0, version_label="v1.0",
            content="Autonomous AI agents must obtain human-in-the-loop signoff for financial trades above $50,000. Takes effect in 2028.",
            is_active=False, status="draft", created_by_id=1,
            effective_date=date(2028, 1, 1)
        )
        db.session.add(v1_fut)

        # Seed Facts
        f1 = PolicyFact(policy_id=1, version_id=1, subject="remote work", predicate="allowed_days", value="1 day per week", confidence=0.98)
        f2 = PolicyFact(policy_id=1, version_id=2, subject="remote work", predicate="allowed_days", value="3 days per week", confidence=0.98)
        f3 = PolicyFact(policy_id=1, version_id=2, subject="internet allowance", predicate="monthly_allowance", value="500 INR", confidence=0.98)
        db.session.add_all([f1, f2, f3])

        # Seed Chunks for hybrid search
        c1 = PolicyChunkV2(id=1, chunk_id="chk_1", policy_id=1, version_id=1, text=v1_remote.content, text_hash="hash_c1")
        c2 = PolicyChunkV2(id=2, chunk_id="chk_2", policy_id=1, version_id=2, text=v2_remote.content, text_hash="hash_c2")
        c3 = PolicyChunkV2(id=3, chunk_id="chk_3", policy_id=2, version_id=3, text=v1_sec.content, text_hash="hash_c3")
        c4 = PolicyChunkV2(id=4, chunk_id="chk_4", policy_id=3, version_id=4, text=v1_exp.content, text_hash="hash_c4")
        c5 = PolicyChunkV2(id=5, chunk_id="chk_5", policy_id=4, version_id=5, text=v1_fut.content, text_hash="hash_c5")
        db.session.add_all([c1, c2, c3, c4, c5])

        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()

class TestPhase5TemporalCorrectness:
    def test_current_question_against_active_policy(self, audit_app):
        """Current question against active policy should resolve active v2.0."""
        resolver = VersionResolver()
        active_ver = resolver.get_active_version(policy_id=1, target_date=date(2024, 6, 1))
        assert active_ver is not None
        assert active_ver.version_num == 2.0
        assert active_ver.is_active is True

    def test_historical_question_against_earlier_version(self, audit_app):
        """Historical query with 2022 date should resolve v1.0."""
        resolver = VersionResolver()
        hist_ver = resolver.get_active_version(policy_id=1, target_date=date(2022, 6, 1))
        assert hist_ver is not None
        assert hist_ver.version_num == 1.0

    def test_superseded_version_semantic_separation(self, audit_app):
        """Verify that v1.0 and v2.0 have different entitlements."""
        v1 = PolicyVersion.query.filter_by(policy_id=1, version_num=1.0).first()
        v2 = PolicyVersion.query.filter_by(policy_id=1, version_num=2.0).first()
        assert "1 day" in v1.content
        assert "3 days" in v2.content

    def test_query_date_before_effective_date_behavior(self, audit_app):
        """
        AUDIT CHECK: What does get_active_version do if date is 2020 (before policy created in 2022)?
        Discovered behavior: returns earliest version instead of None.
        """
        resolver = VersionResolver()
        early_ver = resolver.get_active_version(policy_id=1, target_date=date(2020, 1, 1))
        # Veritas implementation currently returns versions[-1] (earliest) rather than None
        # Recording this design limitation:
        assert early_ver is not None
        assert early_ver.version_num == 1.0

    def test_query_date_after_expiration_behavior(self, audit_app):
        """
        AUDIT CHECK: Query date in 2025 for a policy that expired in 2021 (Policy 3).
        Discovered behavior: returns versions[0] rather than None.
        """
        resolver = VersionResolver()
        exp_ver = resolver.get_active_version(policy_id=3, target_date=date(2025, 1, 1))
        # Records that VersionResolver does not fail closed/abstain on expired intervals
        assert exp_ver is not None

    def test_version_diff_clause_level(self, audit_app):
        """Version comparison where clauses were modified and added."""
        v1 = PolicyVersion.query.filter_by(policy_id=1, version_num=1.0).first()
        v2 = PolicyVersion.query.filter_by(policy_id=1, version_num=2.0).first()
        from rag.versions.diff_engine import PolicyDiffEngine
        differ = PolicyDiffEngine()
        diff = differ.compute_diff(v1.content, v2.content)
        assert len(diff["added_clauses"]) > 0 or len(diff["changed_clauses"]) > 0


class TestPhase5AuthorizationCorrectness:
    def test_authorized_user_access(self, audit_app):
        """Admin is authorized for restricted cybersecurity plan."""
        filter_eng = EvidenceFilter()
        p_sec = Policy.query.get(2)
        u_admin = User.query.get(1)
        scope_admin = QueryScope.from_user(u_admin)
        assert filter_eng.is_authorized_for_policy(scope_admin, p_sec) is True

    def test_unauthorized_user_access_blocked(self, audit_app):
        """Employee in Engineering is NOT authorized for restricted cybersecurity plan."""
        filter_eng = EvidenceFilter()
        p_sec = Policy.query.get(2)
        u_eng = User.query.get(3)
        scope_eng = QueryScope.from_user(u_eng)
        assert filter_eng.is_authorized_for_policy(scope_eng, p_sec) is False

    def test_two_roles_identical_question(self, audit_app):
        """Identical query evaluated under Admin vs Employee yields different authorization scopes."""
        p_sec = Policy.query.get(2)
        scope_admin = QueryScope.from_user(User.query.get(1))
        scope_eng = QueryScope.from_user(User.query.get(3))
        filter_eng = EvidenceFilter()
        auth_admin = filter_eng.is_authorized_for_policy(scope_admin, p_sec)
        auth_eng = filter_eng.is_authorized_for_policy(scope_eng, p_sec)
        assert auth_admin is True
        assert auth_eng is False

    def test_cache_scope_isolation_authorized_then_unauthorized(self, audit_app):
        """
        SECURITY REQUIREMENT: Cache warm-up by authorized user must NOT leak to unauthorized user.
        """
        cache = get_cache()
        scope_admin = QueryScope.from_user(User.query.get(1))
        scope_eng = QueryScope.from_user(User.query.get(3))

        dummy_emb = [0.1] * 384
        # Admin caches answer using put()
        cache.put(dummy_emb, answer="Restricted keyvault token: ALPHA-99-SECRET",
                  citations=[{"policy_id": 2, "version": "1.0"}], chunks_used=1,
                  scope=scope_admin, confidence=0.99)

        # Eng user attempts to retrieve
        leak_res = cache.get(dummy_emb, scope=scope_eng)
        assert leak_res is None, "CRITICAL LEAK: Unauthorized user accessed cached privileged answer!"

    def test_cache_scope_temporal_isolation(self, audit_app):
        """Queries for 2022 vs 2024 must not collide in cache."""
        cache = get_cache()
        resolver = VersionResolver()
        t_2022 = resolver.resolve_temporal_context("in 2022")
        t_2024 = resolver.resolve_temporal_context("in 2024")

        u = User.query.get(3)
        scope_2022 = QueryScope.from_user(u, t_2022)
        scope_2024 = QueryScope.from_user(u, t_2024)

        dummy_emb = [0.2] * 384
        cache.put(dummy_emb, answer="v1 2022 rule: 1 day remote",
                  citations=[{"policy_id": 1, "version": "1.0"}], chunks_used=1,
                  scope=scope_2022, confidence=0.95)

        hit_2024 = cache.get(dummy_emb, scope=scope_2024)
        assert hit_2024 is None, "Temporal cache collision: 2024 query received 2022 cached entry!"


class TestPhase6GroundingAndAbstention:
    def test_direct_question_answered_by_valid_evidence(self, audit_app):
        """Question with valid evidence is verified (or safely UNKNOWN if no neural NLI)."""
        verifier = EntailmentVerifier()
        premise = "Employees may work remotely up to 3 days per week."
        hypothesis = "Under the remote work policy, employees can work remotely 3 days each week."
        res = verifier.verify(hypothesis, [{"text": premise}])
        if verifier._nli_model is not None:
            assert res.is_entailed is True
            assert res.verdict == "ENTAILMENT"
        else:
            # Fallback fail-closed behavior without PyTorch
            assert res.verdict == "UNKNOWN"
            assert res.is_entailed is False

    def test_question_with_contradictory_evidence(self, audit_app):
        """Contradictory hypothesis must be flagged as non-entailed/contradiction."""
        verifier = EntailmentVerifier()
        premise = "Employees may work remotely up to 3 days per week."
        hypothesis = "Remote work is strictly prohibited and all employees must be in the office 5 days."
        res = verifier.verify(hypothesis, [{"text": premise}])
        assert res.is_entailed is False

    def test_unsupported_hallucinated_fact(self, audit_app):
        """Fact not mentioned in premise is rejected."""
        verifier = EntailmentVerifier()
        premise = "Employees may work remotely up to 3 days per week."
        hypothesis = "The company provides free gourmet lunches on Fridays."
        res = verifier.verify(hypothesis, [{"text": premise}])
        assert res.is_entailed is False

    def test_safe_abstention_on_empty_authorized_evidence(self, audit_app):
        """When candidate evidence is filtered to empty, engine abstains."""
        filter_eng = EvidenceFilter()
        scope_eng = QueryScope.from_user(User.query.get(3))
        # Only restricted chunk available
        raw_candidates = [{"chunk_id": "c3", "policy_id": 2, "confidentiality": "restricted", "department_id": 3}]
        filtered = filter_eng.filter_chunks(raw_candidates, scope_eng)
        assert len(filtered) == 0
