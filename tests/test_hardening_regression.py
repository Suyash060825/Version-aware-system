"""
tests/test_hardening_regression.py
Comprehensive regression test suite for publication-grade hardening.
Covers Fact Resolution, Temporal Semantics, Authorization, Canonical QA, FAISS Indexing,
MultiLevelCache, and Citation Validation.
"""
import pytest
from datetime import date
from app import create_app
from models import db, Policy, PolicyVersion, PolicyChunkV2, PolicyFact, CanonicalQuestion, CompiledAnswer, User, PolicyStatus, ConfidentialityLevel

@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

def test_temporal_interval_parsing(app):
    from rag.versions.resolver import VersionResolver
    resolver = VersionResolver()

    # 1. Before Date
    tq = resolver.parse_temporal_query("What was the leave policy before July 2025?")
    assert tq.end_date == date(2025, 6, 30)
    assert tq.historical is True

    # 2. After Date
    tq2 = resolver.parse_temporal_query("What are the rules after January 2024?")
    assert tq2.start_date == date(2024, 2, 1)

    # 3. During Month
    tq3 = resolver.parse_temporal_query("What was the travel policy during June 2024?")
    assert tq3.start_date == date(2024, 6, 1)
    assert tq3.end_date == date(2024, 6, 30)

    # 4. Between Dates
    tq4 = resolver.parse_temporal_query("What was the policy between 2022 and 2023?")
    assert tq4.start_date == date(2022, 1, 1)
    assert tq4.end_date == date(2023, 12, 31)

    # 5. Version comparison
    tq5 = resolver.parse_temporal_query("Compare v1 vs v2 of leave policy")
    assert tq5.comparison_versions == ("1", "2")
    assert tq5.historical is True

def test_fact_resolver_with_source_chunk_and_auth(app):
    from rag.facts.fact_resolver import FactResolver
    from rag.engine.query_scope import QueryScope

    u_eng = User(name="eng_user", email="eng@test.com", password_hash="h", role="employee", department_id=2)
    u_hr = User(name="hr_user", email="hr@test.com", password_hash="h", role="hr", department_id=1)
    db.session.add_all([u_eng, u_hr])
    db.session.commit()

    p = Policy(policy_id="POL-LEAVE", title="Leave Policy", author_id=u_hr.id, status=PolicyStatus.ACTIVE, confidentiality=ConfidentialityLevel.INTERNAL)
    db.session.add(p)
    db.session.commit()

    v = PolicyVersion(
        policy_id=p.id, version_num=1.0, version_label="v1.0",
        effective_date=date(2024, 1, 1), is_active=True,
        content="Employees receive 30 days of annual leave.", created_by_id=u_hr.id
    )
    db.session.add(v)
    db.session.commit()

    c = PolicyChunkV2(
        chunk_id="chunk-leave-1", policy_id=p.id, version_id=v.id,
        section_path="1. Annual Leave", text="Employees receive 30 days of annual leave.",
        page=1, paragraph_num=1, char_count=40, text_hash="hash_leave_1"
    )
    db.session.add(c)
    db.session.commit()

    f = PolicyFact(
        policy_id=p.id, version_id=v.id, subject="annual leave", predicate="annual_leave",
        value="30", unit="days", source_chunk_id="chunk-leave-1", confidence=0.98
    )
    db.session.add(f)
    db.session.commit()

    resolver = FactResolver()
    scope = QueryScope.from_user(u_eng)
    res = resolver.try_resolve("How many days of annual leave are allowed?", scope=scope, user=u_eng)

    assert res.found is True
    assert res.value == "30"
    assert res.unit == "days"
    assert res.source_chunk_id == "chunk-leave-1"
    assert len(res.citations) == 1
    assert res.citations[0]["policy_id"] == p.id
    assert res.citations[0]["section"] == "1. Annual Leave"

def test_authorization_matrix(app):
    from rag.authorization.evidence_filter import EvidenceFilter
    from rag.engine.query_scope import QueryScope

    u_eng = User(name="eng_user", email="eng2@test.com", password_hash="h", role="employee", department_id=2)
    u_hr = User(name="hr_user", email="hr2@test.com", password_hash="h", role="hr", department_id=1)
    u_exec = User(name="exec_user", email="exec@test.com", password_hash="h", role="executive", department_id=3)
    db.session.add_all([u_eng, u_hr, u_exec])
    db.session.commit()

    p_pub = Policy(policy_id="POL-PUB", title="Public Policy", author_id=u_hr.id, status=PolicyStatus.ACTIVE, confidentiality=ConfidentialityLevel.PUBLIC)
    p_conf_hr = Policy(policy_id="POL-HR-CONF", title="HR Confidential", author_id=u_hr.id, status=PolicyStatus.ACTIVE, department_id=1, confidentiality=ConfidentialityLevel.CONFIDENTIAL)
    p_restr = Policy(policy_id="POL-RESTR", title="Executive Strategy", author_id=u_exec.id, status=PolicyStatus.ACTIVE, confidentiality=ConfidentialityLevel.RESTRICTED)
    db.session.add_all([p_pub, p_conf_hr, p_restr])
    db.session.commit()

    ef = EvidenceFilter()

    # Eng user
    scope_eng = QueryScope.from_user(u_eng)
    assert ef.is_authorized_for_policy(scope_eng, p_pub) is True
    assert ef.is_authorized_for_policy(scope_eng, p_conf_hr) is False
    assert ef.is_authorized_for_policy(scope_eng, p_restr) is False

    # HR user
    scope_hr = QueryScope.from_user(u_hr)
    assert ef.is_authorized_for_policy(scope_hr, p_pub) is True
    assert ef.is_authorized_for_policy(scope_hr, p_conf_hr) is True
    assert ef.is_authorized_for_policy(scope_hr, p_restr) is False

    # Executive user
    scope_exec = QueryScope.from_user(u_exec)
    assert ef.is_authorized_for_policy(scope_exec, p_pub) is True
    assert ef.is_authorized_for_policy(scope_exec, p_conf_hr) is True
    assert ef.is_authorized_for_policy(scope_exec, p_restr) is True

def test_canonical_qa_matcher_and_rejection_on_deleted_chunk(app):
    from rag.qa.qa_matcher import QAMatcher
    from rag.qa.qa_index import CanonicalQAIndex
    from rag.engine.query_scope import QueryScope

    u = User(name="admin", email="admin@test.com", password_hash="h", role="admin")
    db.session.add(u)
    db.session.commit()

    p = Policy(policy_id="POL-QA", title="Security Policy", author_id=u.id, status=PolicyStatus.ACTIVE)
    db.session.add(p)
    db.session.commit()

    v = PolicyVersion(policy_id=p.id, version_num=1.0, version_label="v1.0", is_active=True, content="Passwords must be 12 chars.", created_by_id=u.id)
    db.session.add(v)
    db.session.commit()

    c = PolicyChunkV2(
        chunk_id="chunk-sec-1", policy_id=p.id, version_id=v.id,
        section_path="2. Password Rules", text="Passwords must be 12 chars.",
        page=1, paragraph_num=1, char_count=30, text_hash="hash_sec_1"
    )
    db.session.add(c)
    db.session.commit()

    q = CanonicalQuestion(policy_id=p.id, version_id=v.id, source_chunk_id="chunk-sec-1", question="What is minimum password length?", question_hash="qhash1")
    db.session.add(q)
    db.session.commit()

    a = CompiledAnswer(question_id=q.id, answer="The minimum password length is 12 characters.", source_chunk_ids='["chunk-sec-1"]', status="validated", confidence=0.99)
    db.session.add(a)
    db.session.commit()

    # Index into QA Index
    qa_index = CanonicalQAIndex()
    qa_index._init_empty_base()
    qa_index._init_empty_delta()
    qa_index._tombstones = set()
    emb = [0.1] * 384
    qa_index.add([q], [a], [emb])

    matcher = QAMatcher()
    matcher.index = qa_index
    scope = QueryScope.from_user(u)

    # 1. Matching valid question
    res = matcher.match("What is minimum password length?", emb, scope=scope, threshold=0.80)
    assert res is not None
    assert "12 characters" in res["answer"]
    assert res["citations"][0]["chunk_id"] == "chunk-sec-1"

    # 2. Rejection when source chunk is deleted
    db.session.delete(c)
    db.session.commit()

    res_deleted = matcher.match("What is minimum password length?", emb, scope=scope, threshold=0.80)
    assert res_deleted is None

def test_semantic_cache_scope_isolation_and_invalidation(app):
    from rag.cache.semantic_cache import MultiLevelCache
    from rag.engine.query_scope import QueryScope

    cache = MultiLevelCache()
    u_hr = User(name="hr_u", email="hr_cache@test.com", password_hash="h", role="hr", department_id=1)
    u_eng = User(name="eng_u", email="eng_cache@test.com", password_hash="h", role="employee", department_id=2)
    db.session.add_all([u_hr, u_eng])
    db.session.commit()

    p = Policy(policy_id="POL-CACHE", title="HR Policy", author_id=u_hr.id, status=PolicyStatus.ACTIVE)
    db.session.add(p)
    db.session.commit()

    v = PolicyVersion(policy_id=p.id, version_num=1.0, version_label="v1.0", content="HR policy text", is_active=True, created_by_id=u_hr.id)
    db.session.add(v)
    db.session.commit()

    c = PolicyChunkV2(chunk_id="chunk-c1", policy_id=p.id, version_id=v.id, text="Cache test chunk", text_hash="h1")
    db.session.add(c)
    db.session.commit()

    scope_hr = QueryScope.from_user(u_hr)
    scope_eng = QueryScope.from_user(u_eng)

    q_vec = [0.2] * 384
    citations = [{"policy_id": p.id, "version_id": v.id, "chunk_id": "chunk-c1", "version": "1.0"}]

    # Put into cache under HR scope
    cache.put(q_vec, "HR confidential answer", citations, 1, scope=scope_hr)

    # Eng scope must miss
    hit_eng = cache.get(q_vec, scope=scope_eng)
    assert hit_eng is None

    # HR scope must hit
    hit_hr = cache.get(q_vec, scope=scope_hr)
    assert hit_hr is not None
    assert hit_hr["answer"] == "HR confidential answer"

    # Targeted invalidation by version
    cache.invalidate_version(p.id, v.id)
    hit_after_invalidation = cache.get(q_vec, scope=scope_hr)
    assert hit_after_invalidation is None

def test_citation_validator_strictness(app):
    from rag.verification.citation_validator import CitationValidator

    u = User(name="admin_cit", email="admin_cit@test.com", password_hash="h", role="admin")
    db.session.add(u)
    db.session.commit()

    p = Policy(policy_id="POL-CIT", title="Citation Verification Policy", author_id=u.id, status=PolicyStatus.ACTIVE)
    db.session.add(p)
    db.session.commit()

    v1 = PolicyVersion(policy_id=p.id, version_num=1.0, version_label="v1.0", content="v1 content", is_active=False, created_by_id=u.id)
    v2 = PolicyVersion(policy_id=p.id, version_num=2.0, version_label="v2.0", content="v2 content", is_active=True, created_by_id=u.id)
    db.session.add_all([v1, v2])
    db.session.commit()

    c1 = PolicyChunkV2(chunk_id="chunk-v1-1", policy_id=p.id, version_id=v1.id, section_path="Section 1", text="v1 content", text_hash="hv1")
    c2 = PolicyChunkV2(chunk_id="chunk-v2-1", policy_id=p.id, version_id=v2.id, section_path="Section 2", text="v2 content", text_hash="hv2")
    db.session.add_all([c1, c2])
    db.session.commit()

    validator = CitationValidator()

    # 1. Valid citation
    valid_input = [{"chunk_id": "chunk-v1-1", "policy_id": p.id, "version_id": v1.id}]
    enriched = validator.validate_and_enrich(valid_input)
    assert len(enriched) == 1
    assert enriched[0]["version"] == "1.0"
    assert enriched[0]["section"] == "Section 1"

    # 2. Nonexistent policy -> rejected
    fake_policy = [{"chunk_id": "fake-chunk", "policy_id": 9999, "version_id": 9999}]
    enriched_fake = validator.validate_and_enrich(fake_policy)
    assert len(enriched_fake) == 0

    # 3. Mismatched version -> rejected
    mismatched = [{"policy_name": "Citation Verification Policy", "version": "99.0"}]
    enriched_mismatch = validator.validate_and_enrich(mismatched)
    assert len(enriched_mismatch) == 0

def test_cache_validation_exception_fails_closed_and_confidence_preserved(app):
    from rag.cache.semantic_cache import MultiLevelCache
    from rag.engine.query_scope import QueryScope
    import unittest.mock

    cache = MultiLevelCache()
    u = User(name="test_u", email="u@test.com", password_hash="h", role="employee")
    db.session.add(u)
    db.session.commit()

    p = Policy(policy_id="POL-CACHE-SEC", title="Sec Policy", author_id=u.id, status=PolicyStatus.ACTIVE)
    db.session.add(p)
    db.session.commit()

    v = PolicyVersion(policy_id=p.id, version_num=1.0, version_label="v1.0", content="Sec text", is_active=True, created_by_id=u.id)
    db.session.add(v)
    db.session.commit()

    c = PolicyChunkV2(chunk_id="chunk-sec-c", policy_id=p.id, version_id=v.id, text="Sec chunk", text_hash="hsec")
    db.session.add(c)
    db.session.commit()

    scope = QueryScope.from_user(u)
    q_vec = [0.3] * 384
    citations = [{"policy_id": p.id, "version_id": v.id, "chunk_id": "chunk-sec-c", "version": "1.0"}]

    # 1. Store with original confidence 0.72
    cache.put(q_vec, "Real confidence answer", citations, 1, scope=scope, confidence=0.72)

    hit = cache.get(q_vec, scope=scope)
    assert hit is not None
    assert hit["confidence"] == 0.72  # Must not be inflated to 100

    # 2. Simulate validation exception (e.g. DB crash during validation) -> MUST FAIL CLOSED (return None)
    with unittest.mock.patch("rag.authorization.evidence_filter.EvidenceFilter.is_authorized_for_policy", side_effect=RuntimeError("DB disconnect")):
        hit_on_error = cache.get(q_vec, scope=scope)
        assert hit_on_error is None  # Cache validation failure becomes cache miss

def test_temporal_failure_handling_and_no_created_at_truth(app):
    u = User(name="admin_temp", email="admin_temp@test.com", password_hash="h", role="admin")
    db.session.add(u)
    db.session.commit()

    p = Policy(policy_id="POL-TEMP-STRICT", title="Strict Temporal", author_id=u.id, status=PolicyStatus.ACTIVE)
    db.session.add(p)
    db.session.commit()

    # Version with NO effective_date
    v = PolicyVersion(policy_id=p.id, version_num=1.0, version_label="v1.0", content="Unresolved eff date", effective_date=None, created_by_id=u.id)
    db.session.add(v)
    db.session.commit()

    # effective_from must be None, NOT created_at
    assert v.effective_from is None
    # Must not authoritatively satisfy specific target date query
    assert v.is_valid_for_date(date(2025, 1, 1)) is False

    # Version with explicit effective_date
    v2 = PolicyVersion(policy_id=p.id, version_num=2.0, version_label="v2.0", content="Resolved eff date", effective_date=date(2025, 1, 1), created_by_id=u.id)
    db.session.add(v2)
    db.session.commit()

    assert v2.effective_from == date(2025, 1, 1)
    assert v2.is_valid_for_date(date(2025, 6, 1)) is True
    assert v2.is_valid_for_date(date(2024, 6, 1)) is False

def test_fact_resolver_ambiguity_margin_and_unauthorized(app):
    from rag.facts.fact_resolver import FactResolver
    from rag.engine.query_scope import QueryScope

    u = User(name="hr_fact", email="hr_fact@test.com", password_hash="h", role="hr", department_id=1)
    db.session.add(u)
    db.session.commit()

    p = Policy(policy_id="POL-FACT-AMBIG", title="Gift Policy", author_id=u.id, status=PolicyStatus.ACTIVE, confidentiality=ConfidentialityLevel.INTERNAL)
    db.session.add(p)
    db.session.commit()

    v = PolicyVersion(policy_id=p.id, version_num=1.0, version_label="v1.0", content="Gift policy content", effective_date=date(2024, 1, 1), is_active=True, created_by_id=u.id)
    db.session.add(v)
    db.session.commit()

    c = PolicyChunkV2(chunk_id="chunk-gift-1", policy_id=p.id, version_id=v.id, section_path="Gifts", text="Gift policy content", text_hash="hgift")
    db.session.add(c)
    db.session.commit()

    # Two competing facts with identical match score but conflicting values
    f1 = PolicyFact(policy_id=p.id, version_id=v.id, subject="gift limit", predicate="gift_limit", value="5000", unit="INR", source_chunk_id="chunk-gift-1", confidence=0.9)
    f2 = PolicyFact(policy_id=p.id, version_id=v.id, subject="gift policy", predicate="gift_limit", value="10000", unit="INR", source_chunk_id="chunk-gift-1", confidence=0.9)
    db.session.add_all([f1, f2])
    db.session.commit()

    resolver = FactResolver()
    scope = QueryScope.from_user(u)

    # 1. Missing scope/user must fail closed
    res_no_auth = resolver.try_resolve("What is the gift limit?", scope=None, user=None)
    assert res_no_auth.found is False

    # 2. Conflicting facts within ambiguity margin must escalate (found=False)
    res_ambig = resolver.try_resolve("What is the gift limit?", scope=scope, user=u)
    assert res_ambig.found is False

def test_faiss_delta_persistence_restart_and_compaction(app, tmp_path):
    from rag.qa.qa_index import CanonicalQAIndex
    import os

    u = User(name="admin_faiss", email="admin_faiss@test.com", password_hash="h", role="admin")
    db.session.add(u)
    db.session.commit()

    p = Policy(policy_id="POL-FAISS", title="Faiss Policy", author_id=u.id, status=PolicyStatus.ACTIVE)
    db.session.add(p)
    db.session.commit()

    v = PolicyVersion(policy_id=p.id, version_num=1.0, version_label="v1.0", content="Content", is_active=True, created_by_id=u.id)
    db.session.add(v)
    db.session.commit()

    c = PolicyChunkV2(chunk_id="chunk-f-1", policy_id=p.id, version_id=v.id, text="Faiss test", text_hash="hf1")
    db.session.add(c)
    db.session.commit()

    q1 = CanonicalQuestion(policy_id=p.id, version_id=v.id, source_chunk_id="chunk-f-1", question="What is policy A?", question_hash="q1")
    q2 = CanonicalQuestion(policy_id=p.id, version_id=v.id, source_chunk_id="chunk-f-1", question="What is policy B?", question_hash="q2")
    db.session.add_all([q1, q2])
    db.session.commit()

    a1 = CompiledAnswer(question_id=q1.id, answer="Policy A answer", source_chunk_ids='["chunk-f-1"]', status="validated")
    a2 = CompiledAnswer(question_id=q2.id, answer="Policy B answer", source_chunk_ids='["chunk-f-1"]', status="validated")
    db.session.add_all([a1, a2])
    db.session.commit()

    index_file = str(tmp_path / "test_faiss.index")
    meta_file = str(tmp_path / "test_faiss.meta.pkl")
    delta_file = str(tmp_path / "test_faiss_delta.index")

    idx = CanonicalQAIndex(dimension=384)
    idx.INDEX_FILE = index_file
    idx.META_FILE = meta_file
    idx.DELTA_INDEX_FILE = delta_file

    emb1 = [0.1] * 384
    emb2 = [0.2] * 384

    # Add base and delta items
    idx.rebuild_from_db()
    idx.add([q2], [a2], [emb2])
    idx.save()

    # Destroy object and reload
    idx_reloaded = CanonicalQAIndex(dimension=384)
    idx_reloaded.INDEX_FILE = index_file
    idx_reloaded.META_FILE = meta_file
    idx_reloaded.DELTA_INDEX_FILE = delta_file
    idx_reloaded.load()

    # Search should find both
    res = idx_reloaded.search(emb2, top_k=2)
    assert len(res) >= 1
    assert any(r[2] == q2.id for r in res)

    # Tombstone q2 and compact
    idx_reloaded.delete_policy_version(p.id, v.id)
    res_tombstoned = idx_reloaded.search(emb2, top_k=2)
    assert len(res_tombstoned) == 0

    idx_reloaded.compact()
    assert len(idx_reloaded._metadata) == 0

def test_user_explicit_capabilities(app):
    u_emp = User(name="emp", email="emp_cap@test.com", password_hash="h", role="employee", department_id=1)
    u_mgr = User(name="mgr", email="mgr_cap@test.com", password_hash="h", role="manager", department_id=1)
    u_hr = User(name="hr", email="hr_cap@test.com", password_hash="h", role="hr", department_id=2)
    u_exec = User(name="exec", email="exec_cap@test.com", password_hash="h", role="executive", department_id=3)
    u_admin = User(name="admin", email="admin_cap@test.com", password_hash="h", role="admin")
    db.session.add_all([u_emp, u_mgr, u_hr, u_exec, u_admin])
    db.session.commit()

    p_conf_dept1 = Policy(policy_id="POL-C1", title="C1", author_id=u_admin.id, department_id=1, confidentiality=ConfidentialityLevel.CONFIDENTIAL)
    p_conf_dept2 = Policy(policy_id="POL-C2", title="C2", author_id=u_admin.id, department_id=2, confidentiality=ConfidentialityLevel.CONFIDENTIAL)
    p_restr = Policy(policy_id="POL-R", title="R", author_id=u_admin.id, confidentiality=ConfidentialityLevel.RESTRICTED)
    db.session.add_all([p_conf_dept1, p_conf_dept2, p_restr])
    db.session.commit()

    # 1. Internal
    assert u_emp.can_view_internal() is True

    # 2. Confidential
    assert u_emp.can_view_confidential(p_conf_dept1) is True
    assert u_emp.can_view_confidential(p_conf_dept2) is False
    assert u_mgr.can_view_confidential(p_conf_dept1) is True
    assert u_mgr.can_view_confidential(p_conf_dept2) is False
    assert u_hr.can_view_confidential(p_conf_dept1) is True  # HR can view all confidential
    assert u_admin.can_view_confidential(p_conf_dept1) is True

    # 3. Restricted
    assert u_emp.can_view_restricted(p_restr) is False
    assert u_mgr.can_view_restricted(p_restr) is False
    assert u_hr.can_view_restricted(p_restr) is False
    assert u_exec.can_view_restricted(p_restr) is True
    assert u_admin.can_view_restricted(p_restr) is True

    # 4. Approvals
    assert u_mgr.can_approve_policy(p_conf_dept1) is True
    assert u_mgr.can_approve_policy(p_conf_dept2) is False
    assert u_hr.can_approve_policy(p_conf_dept1) is True
    assert u_admin.can_approve_policy(p_conf_dept1) is True

def test_production_config_secret_validation(monkeypatch):
    from config import ProductionConfig
    monkeypatch.setenv("SECRET_KEY", "change-this-in-production-please")
    with pytest.raises(ValueError):
        ProductionConfig.validate_production_secrets()

    monkeypatch.setenv("SECRET_KEY", "ultra-secure-randomly-generated-production-key-999")
    monkeypatch.setenv("JWT_SECRET_KEY", "ultra-secure-randomly-generated-jwt-key-999")
    monkeypatch.setenv("DEFAULT_ADMIN_PASSWORD", "ultra-secure-admin-pass-999!")
    # Must pass without raising
    ProductionConfig.validate_production_secrets()

    # Missing admin password must raise
    monkeypatch.setenv("DEFAULT_ADMIN_PASSWORD", "")
    with pytest.raises(ValueError):
        ProductionConfig.validate_production_secrets()

def test_version_comparison_pre_authorization_and_refusal(app):
    from rag.engine.query_engine import get_query_engine

    u_emp = User(name="emp_cmp", email="emp_cmp@test.com", password_hash="h", role="employee", department_id=1)
    u_exec = User(name="exec_cmp", email="exec_cmp@test.com", password_hash="h", role="executive", department_id=3)
    db.session.add_all([u_emp, u_exec])
    db.session.commit()

    # Restricted Policy (only accessible by Executive / Admin)
    p_restr = Policy(policy_id="POL-CMP-RESTR", title="Executive Compensation Strategy", author_id=u_exec.id, status=PolicyStatus.ACTIVE, confidentiality=ConfidentialityLevel.RESTRICTED)
    db.session.add(p_restr)
    db.session.commit()

    v1 = PolicyVersion(policy_id=p_restr.id, version_num=1.0, version_label="v1.0", content="Executive bonus is 20 percent of salary.", effective_date=date(2023, 1, 1), created_by_id=u_exec.id)
    v2 = PolicyVersion(policy_id=p_restr.id, version_num=2.0, version_label="v2.0", content="Executive bonus is 35 percent of salary.", effective_date=date(2024, 1, 1), is_active=True, created_by_id=u_exec.id)
    db.session.add_all([v1, v2])
    db.session.commit()

    engine = get_query_engine()

    # 1. Unauthorized employee attempting version comparison on restricted policy MUST BE REFUSED / ABSTAIN
    res_unauth = engine.answer("Compare v1 vs v2 of Executive Compensation Strategy", user=u_emp)
    assert res_unauth.route != "TEMPORAL_COMPARISON"
    assert "Executive bonus is 35" not in res_unauth.answer
    assert "20 percent" not in res_unauth.answer

    # 2. Authorized executive attempting version comparison receives authoritative diff
    res_auth = engine.answer("Compare v1 vs v2 of Executive Compensation Strategy", user=u_exec)
    assert res_auth.route == "TEMPORAL_COMPARISON"
    assert "Executive Compensation Strategy" in res_auth.answer
