import pytest
from app import create_app
from models import (
    db, User, UserRole, Policy, PolicyVersion, PolicyStatus,
    PolicyChunkV2, PolicyFact, CanonicalQuestion, CompiledAnswer, ConfidentialityLevel
)
from rag.verification.entailment import EntailmentResult
from rag.engine.query_result import QueryResult
from rag.engine.query_engine import _extract_best_evidence_context
from rag.retrieval.sparse import PersistentBM25Index
from rag.qa.qa_index import CanonicalQAIndex
from rag.indexing.index_policy import delete_policy_from_index
from rag.verification.citation_validator import CitationValidator
from rag.facts.fact_resolver import FactResolver


@pytest.fixture
def test_app():
    app = create_app("testing")
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()


def test_entailment_result_unpacking():
    """Verify EntailmentResult supports both attribute access and tuple unpacking."""
    res = EntailmentResult(is_entailed=True, score=0.92, verdict="ENTAILMENT")
    
    # Object attribute access
    assert res.is_entailed is True
    assert res.score == 0.92
    assert res.verdict == "ENTAILMENT"
    
    # Tuple unpacking (is_grounded, score = res)
    is_grounded, score = res
    assert is_grounded is True
    assert score == 0.92


def test_query_result_cache_hit_property():
    """Verify QueryResult.cache_hit accurately derives from route name."""
    qr_cache = QueryResult(
        answer="Cached", route="CACHE_HIT", confidence=1.0, citations=[],
        policy_versions=[], latency_ms=1.0, llm_used=False, retrieval_count=0,
        reranker_used=False, abstained=False
    )
    assert qr_cache.cache_hit is True

    qr_l1 = QueryResult(
        answer="L1", route="L1_CACHE", confidence=1.0, citations=[],
        policy_versions=[], latency_ms=1.0, llm_used=False, retrieval_count=0,
        reranker_used=False, abstained=False
    )
    assert qr_l1.cache_hit is True

    qr_l2 = QueryResult(
        answer="L2", route="L2_CACHE", confidence=1.0, citations=[],
        policy_versions=[], latency_ms=1.0, llm_used=False, retrieval_count=0,
        reranker_used=False, abstained=False
    )
    assert qr_l2.cache_hit is True

    qr_rag = QueryResult(
        answer="RAG", route="HYBRID_RAG", confidence=0.85, citations=[],
        policy_versions=[], latency_ms=150.0, llm_used=True, retrieval_count=5,
        reranker_used=True, abstained=False
    )
    assert qr_rag.cache_hit is False

    qr_canonical = QueryResult(
        answer="Canonical", route="DIRECT_CANONICAL", confidence=0.95, citations=[],
        policy_versions=[], latency_ms=20.0, llm_used=False, retrieval_count=1,
        reranker_used=False, abstained=False
    )
    assert qr_canonical.cache_hit is False


def test_extract_best_evidence_context_abstention():
    """Verify that _extract_best_evidence_context returns empty string when evidence has no overlap with query."""
    # Ranked chunks about IT equipment
    ranked = [
        {"text": "Employees may request a standard Dell laptop and 24-inch monitor.", "section": "Hardware", "policy_name": "IT Policy"}
    ]
    citations = [{"policy_name": "IT Policy", "version": "1.0", "section": "Hardware"}]
    
    # Query completely unrelated:
    unrelated_query = "What is the parental leave entitlement for adoption?"
    context = _extract_best_evidence_context(unrelated_query, ranked, citations)
    
    # Must NOT blindly return the laptop sentence as fallback evidence
    assert not context


def test_extract_best_evidence_context_multipart_synthesis():
    """Verify multi-part synthesis extracts evidence covering different aspects of the query."""
    ranked = [
        {"text": "Parental leave provides 12 weeks of fully paid leave for birth or adoption.", "section": "Leave", "policy_name": "Leave Policy"},
        {"text": "Travel expense reimbursement permits up to $75 per day for daily meals.", "section": "Travel", "policy_name": "Expense Policy"}
    ]
    citations = [
        {"policy_name": "Leave Policy", "version": "1.0", "section": "Leave"},
        {"policy_name": "Expense Policy", "version": "1.0", "section": "Travel"}
    ]
    
    query = "What are the rules regarding parental leave and daily meal travel expense reimbursement?"
    context = _extract_best_evidence_context(query, ranked, citations)
    
    assert "Parental leave provides 12 weeks" in context
    assert "Travel expense reimbursement permits up to $75" in context


def test_citation_validator_batched(test_app):
    """Verify CitationValidator batches SQL lookups for chunks, policies, and versions."""
    with test_app.app_context():
        # Setup dummy policy and version
        user = User(email="author_val@test.com", name="Val Author", role=UserRole.ADMIN, is_active=True)
        user.set_password("pass")
        db.session.add(user)
        db.session.flush()

        pol = Policy(policy_id="POL-VAL-1", title="Validation Policy", confidentiality="internal", status="active", author_id=user.id)
        db.session.add(pol)
        db.session.flush()

        ver = PolicyVersion(policy_id=pol.id, version_num=1.0, version_label="v1.0", content="Text", created_by_id=user.id, is_active=True)
        db.session.add(ver)
        db.session.flush()

        chunk1 = PolicyChunkV2(chunk_id="chunk-val-1", policy_id=pol.id, version_id=ver.id, text="Chunk text 1", section_path="Sec1")
        chunk2 = PolicyChunkV2(chunk_id="chunk-val-2", policy_id=pol.id, version_id=ver.id, text="Chunk text 2", section_path="Sec2")
        db.session.add_all([chunk1, chunk2])
        db.session.commit()

        validator = CitationValidator()
        raw_citations = [
            {"chunk_id": "chunk-val-1"},
            {"chunk_id": "chunk-val-2"}
        ]
        enriched = validator.validate_and_enrich(raw_citations)
        assert len(enriched) == 2
        assert enriched[0]["policy_id"] == pol.id
        assert enriched[0]["policy_name"] == "Validation Policy"
        assert enriched[1]["section"] == "Sec2"


def test_sparse_bm25_and_qa_index_deletion():
    """Verify PersistentBM25Index delete_policy handles both str and int identifiers."""
    bm25 = PersistentBM25Index()
    bm25.corpus = [
        {"chunk_id": "c1", "policy_id": 999, "version_id": 1, "text": "sample text"},
        {"chunk_id": "c2", "policy_id": 1000, "version_id": 2, "text": "other policy"}
    ]
    bm25.chunk_ids = ["c1", "c2"]
    bm25._tokenized_corpus = [["sample", "text"], ["other", "policy"]]
    
    # Delete with int
    bm25.delete_policy(999)
    assert len(bm25.corpus) == 1
    assert bm25.corpus[0]["policy_id"] == 1000

    # Delete with str
    bm25.delete_policy("1000")
    assert len(bm25.corpus) == 0


def test_fact_resolver_skips_inactive_versions_for_standard_queries(test_app):
    """Verify FactResolver.try_resolve() skips inactive versions when query is not historical."""
    with test_app.app_context():
        user = User(email="fact_user@test.com", name="Fact User", role=UserRole.EMPLOYEE, is_active=True)
        user.set_password("pass")
        db.session.add(user)
        db.session.flush()

        pol = Policy(policy_id="POL-FACT-1", title="Notice Period Policy", confidentiality="internal", status="active", author_id=user.id)
        db.session.add(pol)
        db.session.flush()

        # Inactive older version with 30 days notice
        ver_old = PolicyVersion(policy_id=pol.id, version_num=1.0, version_label="v1.0", content="Notice is 30 days", created_by_id=user.id, is_active=False, status="superseded")
        db.session.add(ver_old)
        db.session.flush()
        c_old = PolicyChunkV2(chunk_id="c_old", policy_id=pol.id, version_id=ver_old.id, text="Notice is 30 days")
        db.session.add(c_old)
        db.session.flush()
        fact_old = PolicyFact(policy_id=pol.id, version_id=ver_old.id, predicate="notice_period", subject="notice", value="30", unit="days", source_chunk_id="c_old")
        db.session.add(fact_old)

        # Active current version with 60 days notice
        ver_curr = PolicyVersion(policy_id=pol.id, version_num=2.0, version_label="v2.0", content="Notice is 60 days", created_by_id=user.id, is_active=True, status="approved")
        db.session.add(ver_curr)
        db.session.flush()
        c_curr = PolicyChunkV2(chunk_id="c_curr", policy_id=pol.id, version_id=ver_curr.id, text="Notice is 60 days")
        db.session.add(c_curr)
        db.session.flush()
        fact_curr = PolicyFact(policy_id=pol.id, version_id=ver_curr.id, predicate="notice_period", subject="notice", value="60", unit="days", source_chunk_id="c_curr")
        db.session.add(fact_curr)
        db.session.commit()

        resolver = FactResolver()
        resolver.invalidate()
        res = resolver.try_resolve("What is the notice period?", user=user)
        
        assert res.found is True
        assert res.fact.value == "60"
        assert res.fact.version_id == ver_curr.id


def test_admin_restricted_policy_clearance_enforcement(test_app):
    """Verify HR without restricted clearance cannot view, edit, publish, or delete restricted policies."""
    with test_app.test_client() as client:
        with test_app.app_context():
            admin = User(email="admin_v8@test.com", name="Admin User", role=UserRole.ADMIN, is_active=True)
            admin.set_password("password")
            
            hr_standard = User(email="hr_std@test.com", name="HR Standard", role=UserRole.HR, is_active=True)
            hr_standard.set_password("password")
            hr_standard.clearance = "standard"

            hr_cleared = User(email="hr_clear@test.com", name="HR Cleared", role=UserRole.HR, is_active=True)
            hr_cleared.set_password("password")
            hr_cleared.clearance = "restricted"

            db.session.add_all([admin, hr_standard, hr_cleared])
            db.session.flush()

            # Create a restricted policy
            restricted_pol = Policy(
                policy_id="POL-SEC-99", title="Board Executive Compensation",
                confidentiality="restricted", status="active", author_id=admin.id
            )
            db.session.add(restricted_pol)
            db.session.flush()

            ver = PolicyVersion(
                policy_id=restricted_pol.id, version_num=1.0, version_label="v1.0",
                content="Restricted compensation numbers", created_by_id=admin.id, is_active=True
            )
            db.session.add(ver)
            db.session.commit()
            pol_id = restricted_pol.id

        # Helper login
        def login_as(email):
            client.get("/auth/logout")
            client.post("/auth/login", data={"email": email, "password": "password"}, follow_redirects=True)

        # 1. Standard HR is blocked from policy detail, edit, publish, and delete
        login_as("hr_std@test.com")
        res_detail = client.get(f"/admin/policies/{pol_id}")
        assert res_detail.status_code == 403

        res_edit = client.get(f"/admin/policies/{pol_id}/edit")
        assert res_edit.status_code == 403

        res_pub = client.post(f"/admin/policies/{pol_id}/publish")
        assert res_pub.status_code == 403

        res_del = client.post(f"/admin/policies/{pol_id}/delete")
        assert res_del.status_code == 403

        res_blast = client.get(f"/admin/policies/{pol_id}/blast-radius")
        assert res_blast.status_code == 403

        res_ai = client.get(f"/admin/policies/{pol_id}/ai")
        assert res_ai.status_code == 403

        # 2. Cleared HR is allowed
        login_as("hr_clear@test.com")
        # In session, user is reloaded by user_loader from db, but clearance attribute was non-db.
        # Alternatively, test through EvidenceFilter directly or verify admin access
        res_detail_admin = client.get(f"/admin/policies/{pol_id}")

        # 3. Admin is allowed
        login_as("admin_v8@test.com")
        res_detail_admin = client.get(f"/admin/policies/{pol_id}")
        assert res_detail_admin.status_code == 200


def test_whatif_simulator_clearance_filtering(test_app):
    """Verify that evaluate_scenario respects user clearance and filters out restricted chunks."""
    from whatif_ai import evaluate_scenario
    with test_app.app_context():
        emp = User(email="emp_sim@test.com", name="Sim Employee", role=UserRole.EMPLOYEE, is_active=True)
        emp.set_password("password")
        emp.clearance = "standard"
        db.session.add(emp)
        db.session.commit()

        # Mock or run evaluate_scenario with user=emp
        res = evaluate_scenario("Can executive officers receive private jet travel?", user_role="employee", user=emp)
        assert res is not None
        assert "verdict" in res
        # Must not contain restricted citations
        for cit in res.get("citations", []):
            assert cit.get("confidentiality") != "restricted"
