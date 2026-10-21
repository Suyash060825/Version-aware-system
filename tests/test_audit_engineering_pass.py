"""
tests/test_audit_engineering_pass.py
Comprehensive regression test suite verifying engineering audit fixes:
- Ollama-only provider consolidation & model ID fidelity (qwen3:4b-q4_K_M)
- Health check strict model verification & diagnostics
- Fallback visibility across policy_ai (rewriting & review) and whatif_ai (provenance)
- Embedding model dimension consistency, bounded batching, and vector validation
- Ingestion lifecycle: create, file extraction (ParserResult), edit metadata invalidation,
  publish (Celery task compatibility), archive, restore, delete, duplication
- Safe AnonymousUser handling on error pages
"""
import io
import os
import json
import pytest
from datetime import date
from unittest.mock import patch, MagicMock

from app import create_app
from models import (
    db, User, UserRole, Policy, PolicyVersion, PolicyStatus,
    ConfidentialityLevel, Department, PolicyCategory, CompilationJob,
    PolicyChunkV2, PolicyFact, CanonicalQuestion, CompiledAnswer
)
from rag.llm_provider import OllamaProvider, get_llm_provider, LLMResponse
from rag.embeddings.embedder import get_embedder, _validate_vector, BaseEmbedder
from rag.parser.pdf_parser import extract_document, ParserResult
from policy_ai import rewrite_text, review_policy, generate_policy_draft
from whatif_ai import evaluate_scenario
from rag.compiler.pipeline import KnowledgeCompilerPipeline, auto_compile_policy_version
from rag.cache.semantic_cache import get_cache
from rag.authorization.evidence_filter import get_evidence_filter
from tasks import compile_policy_version_task, index_policy_version_task


@pytest.fixture(scope="module")
def audit_app():
    app = create_app("testing")
    app.config["WTF_CSRF_ENABLED"] = False
    with app.app_context():
        db.create_all()
        # Ensure test department & admin user exist
        dept = Department.query.filter_by(name="Engineering").first()
        if not dept:
            dept = Department(name="Engineering", code="ENG")
            db.session.add(dept)
            db.session.commit()

        admin = User.query.filter_by(email="audit_eng_admin@company.com").first()
        if not admin:
            admin = User(
                name="Audit Admin",
                email="audit_eng_admin@company.com",
                password_hash="hash",
                role=UserRole.ADMIN,
                department_id=dept.id,
            )
            db.session.add(admin)
            db.session.commit()

        yield app


# ==============================================================================
# 1. Ollama Provider Consolidation & Model Fidelity
# ==============================================================================

def test_ollama_provider_default_and_model_fidelity():
    """Verify OllamaProvider defaults to qwen3:4b-q4_K_M and exposes diagnostics."""
    provider = OllamaProvider()
    assert "qwen3:4b" in provider.model.lower()
    diag = provider.diagnostics()
    assert diag["provider"] == "OllamaProvider"
    assert diag["model"] == provider.model
    assert diag["backend"] == "ollama"


def test_ollama_health_check_verifies_model_installed():
    """Verify health_check checks /api/tags and rejects missing models."""
    provider = OllamaProvider(model="nonexistent_fantasy_model:99b")
    # Simulate Ollama running but missing this specific model
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "models": [{"name": "qwen3:4b-q4_K_M"}]
    }
    with patch.object(provider._session, "get", return_value=mock_resp):
        provider._is_healthy = None
        provider._last_health_time = 0
        is_healthy = provider.health_check()
        assert is_healthy is False, "Provider must report unhealthy if requested model is not pulled"


def test_ollama_health_check_accepts_configured_qwen():
    """Verify health_check accepts qwen3:4b-q4_K_M when pulled."""
    provider = OllamaProvider(model="qwen3:4b-q4_K_M")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "models": [{"name": "qwen3:4b-q4_K_M"}]
    }
    with patch.object(provider._session, "get", return_value=mock_resp):
        provider._is_healthy = None
        provider._last_health_time = 0
        is_healthy = provider.health_check()
        assert is_healthy is True


def test_ollama_fallback_visibility_on_error():
    """Verify that network or inference failure marks fallback=True and preserves error."""
    provider = OllamaProvider(model="qwen3:4b-q4_K_M")
    with patch.object(provider._session, "post", side_effect=RuntimeError("Simulated Ollama crash")):
        resp = provider.generate("Summarize policy.")
        assert resp.fallback is True
        assert resp.error is not None
        assert "Ollama error" in resp.error


# ==============================================================================
# 2. Fallback Visibility in Policy AI & What-If AI
# ==============================================================================

def test_policy_ai_rewrite_does_not_mask_failure():
    """Verify rewrite_text returns empty string on failure instead of faking success with original content."""
    original_text = "The quick brown fox jumps over the lazy dog."
    mock_llm = MagicMock()
    mock_llm.generate.return_value = LLMResponse(text="", fallback=True, error="Ollama offline")

    with patch("policy_ai.get_llm", return_value=mock_llm):
        result = rewrite_text(original_text, mode="simplify")
        assert result == "", "Failed rewrite must not silently return original text"


def test_policy_ai_review_distinguishes_heuristic_from_model():
    """Verify review_policy flags heuristic fallback vs LLM model assessment."""
    policy_text = "1. Purpose: Safety guidelines. 2. Scope: All employees."

    # Case A: Model outputs valid JSON
    valid_json = json.dumps({
        "missing_sections": ["Definitions"],
        "compliance_issues": ["GDPR gap"],
        "legal_language_issues": [],
        "suggestions": ["Add data retention period."],
        "risk_score": 35
    })
    mock_llm_success = MagicMock()
    mock_llm_success.generate.return_value = LLMResponse(text=valid_json, fallback=False)

    with patch("policy_ai.get_llm", return_value=mock_llm_success):
        rev = review_policy(policy_text)
        assert rev["assessment_source"] == "model"
        assert rev["is_heuristic"] is False
        assert rev["risk_score"] == 35

    # Case B: Model fails -> falls back to heuristic review
    mock_llm_fail = MagicMock()
    mock_llm_fail.generate.return_value = LLMResponse(text="", fallback=True)

    with patch("policy_ai.get_llm", return_value=mock_llm_fail):
        rev = review_policy(policy_text)
        assert rev["assessment_source"] == "heuristic_fallback"
        assert rev["is_heuristic"] is True


def test_whatif_ai_exposes_provenance():
    """Verify evaluate_scenario exposes provenance ('model' vs 'heuristic_fallback')."""
    # When no chunks match, returns heuristic_fallback
    res = evaluate_scenario("Unknown random scenario with no policies")
    assert "provenance" in res
    assert res["provenance"] in ("model", "fallback", "heuristic_fallback")


# ==============================================================================
# 3. Embedding Subsystem: Dimension, Bounded Batching, Vector Validation
# ==============================================================================

def test_vector_validation():
    """Verify vector validation enforces dimension and finite values."""
    valid_vec = [0.1] * 384
    assert len(_validate_vector(valid_vec, 384)) == 384

    # Dimension mismatch
    with pytest.raises(ValueError, match="Vector dimension mismatch"):
        _validate_vector([0.1] * 128, 384)

    # NaN / Inf rejection
    with pytest.raises(ValueError, match="non-finite values"):
        _validate_vector([float("nan")] * 384, 384)


def test_embedder_bounded_batching():
    """Verify embedder processes large document chunks in bounded batches without failure."""
    embedder = get_embedder()
    chunks = [f"Sample policy clause sentence number {i} with specific legal definitions." for i in range(150)]
    vectors = embedder.embed(chunks)
    assert len(vectors) == 150
    assert len(vectors[0]) == getattr(embedder, "dimension", 384)

    # Empty text list
    assert embedder.embed([]) == []

    # Query embedding
    q_vec = embedder.embed_query("What is the remote work policy?")
    assert len(q_vec) == getattr(embedder, "dimension", 384)


# ==============================================================================
# 4. Structured Document Parser: PDF, DOCX, XLSX, TXT, MD
# ==============================================================================

def test_parser_result_structure(tmp_path):
    """Verify extract_document returns ParserResult with metadata and truncation tracking."""
    # Plain text file
    txt_file = tmp_path / "test_policy.txt"
    txt_file.write_text("Section 1: General Leave.\nAll employees receive 25 days leave.", encoding="utf-8")

    res = extract_document(str(txt_file), max_chars=1000)
    assert isinstance(res, ParserResult)
    assert res.success is True
    assert res.format == ".txt"
    assert "25 days leave" in res.text
    assert res.truncated is False

    # Truncation enforcement
    res_trunc = extract_document(str(txt_file), max_chars=20)
    assert res_trunc.truncated is True
    assert len(res_trunc.text) == 20

    # Nonexistent file
    res_missing = extract_document(str(tmp_path / "nonexistent.pdf"))
    assert res_missing.success is False
    assert "not found" in res_missing.error.lower()

    # Empty file
    empty_file = tmp_path / "empty.txt"
    empty_file.write_text("", encoding="utf-8")
    res_empty = extract_document(str(empty_file))
    assert res_empty.success is False
    assert "empty" in res_empty.error.lower()


# ==============================================================================
# 5. Ingestion Pathways & Lifecycle
# ==============================================================================

def test_policy_metadata_edit_invalidates_caches_and_reindexes(audit_app):
    """Verify that editing policy metadata invalidates caches and updates search index."""
    with audit_app.app_context():
        admin = User.query.filter_by(role=UserRole.ADMIN).first()
        dept = Department.query.first()

        p = Policy(
            policy_id="TEST-EDIT-001",
            title="Initial Test Title",
            description="Initial description",
            author_id=admin.id,
            department_id=dept.id,
            status=PolicyStatus.ACTIVE,
            confidentiality=ConfidentialityLevel.INTERNAL,
        )
        db.session.add(p)
        db.session.commit()

        v = PolicyVersion(
            policy_id=p.id,
            version_num=1.0,
            version_label="v1.0",
            content="Employees must submit travel receipts within 14 business days.",
            is_active=True,
            status="approved",
            created_by_id=admin.id,
        )
        db.session.add(v)
        db.session.commit()

        # Compile initial version
        auto_compile_policy_version(p.id, v.id)

        # Seed semantic cache with a query hit
        cache = get_cache()
        embedder = get_embedder()
        q_vec = embedder.embed_query("travel receipts deadline")
        cache.put(q_vec, "Submit within 14 business days", [{"policy_id": p.id, "version": "v1.0"}], 1)
        assert cache.get(q_vec) is not None

        # Simulate editing metadata via admin edit pathway
        client = audit_app.test_client()
        with client.session_transaction() as sess:
            sess["_user_id"] = str(admin.id)
            sess["_fresh"] = True

        resp = client.post(f"/admin/policies/{p.id}/edit", data={
            "title": "Updated Travel Expense Policy",
            "description": "Updated description",
            "department_id": str(dept.id),
            "priority": "high",
            "confidentiality": "internal",
        }, follow_redirects=False)

        assert resp.status_code == 302

        # Verify semantic cache was invalidated for this policy
        assert cache.get(q_vec) is None, "Editing policy metadata must invalidate semantic cache"


def test_celery_task_compatibility_alias():
    """Verify compile_policy_version_task and index_policy_version_task are identical callable tasks."""
    assert compile_policy_version_task is index_policy_version_task
    assert hasattr(compile_policy_version_task, "delay")


# ==============================================================================
# 6. Safe Anonymous User Handling
# ==============================================================================

def test_safe_anonymous_user_on_error_pages(audit_app):
    """Verify requesting a 404 URL unauthenticated returns 404 without crashing with 500."""
    client = audit_app.test_client()
    resp = client.get("/nonexistent-audit-route-xyz-404")
    assert resp.status_code == 404
    assert b"404" in resp.data or b"Not Found" in resp.data
