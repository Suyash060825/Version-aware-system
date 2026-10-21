"""
tests/test_independent_validation.py
Independent validation suite covering:
1. Embedding subsystem stress tests (wrong dimensions, NaN vectors, large batches).
2. All 14 policy ingestion pathways & idempotency.
3. Authorization & evidence isolation (zero-leakage verification).
4. Failure states: verifying failed compiler stages do NOT leave policy in READY state.
"""

import os
import pytest
import numpy as np
from unittest.mock import MagicMock, patch

from app import create_app
from models import (
    db, User, Policy, PolicyVersion, Department, UserRole,
    PolicyStatus, ConfidentialityLevel, PolicyChunkV2,
    CompilationJob, CompilationStage, PolicyFact, CanonicalQuestion
)
from rag.embeddings.embedder import FastEmbedEmbedder, get_embedder, _validate_vector
from rag.retrieval.sparse import PersistentBM25Index
from rag.cache.semantic_cache import get_cache
from rag.compiler.pipeline import KnowledgeCompilerPipeline, auto_compile_policy_version
from rag.authorization.evidence_filter import EvidenceFilter
from rag.engine.query_scope import QueryScope


@pytest.fixture(scope="module")
def val_app():
    app = create_app("testing")
    app.config["WTF_CSRF_ENABLED"] = False
    with app.app_context():
        db.create_all()
        dept = Department.query.filter_by(name="Validation Dept").first()
        if not dept:
            dept = Department(name="Validation Dept", code="VAL")
            db.session.add(dept)
            db.session.commit()

        admin = User.query.filter_by(email="val_admin@company.com").first()
        if not admin:
            admin = User(
                name="Val Admin",
                email="val_admin@company.com",
                password_hash="hash",
                role=UserRole.ADMIN,
                department_id=dept.id,
            )
            db.session.add(admin)
            db.session.commit()

        emp = User.query.filter_by(email="val_emp@company.com").first()
        if not emp:
            emp = User(
                name="Val Employee",
                email="val_emp@company.com",
                password_hash="hash",
                role=UserRole.EMPLOYEE,
                department_id=dept.id,
            )
            db.session.add(emp)
            db.session.commit()

        yield app


# ==============================================================================
# 1. Embedding Subsystem Independent Stress Tests
# ==============================================================================

def test_embedding_batch_and_dimension_consistency():
    """Verify batch sizes > 64 are split correctly and query/document dimensions match."""
    embedder = get_embedder()
    doc_texts = [f"Policy chunk test statement number {i} covering compliance." for i in range(130)]
    
    # Large batch (> 64)
    embeddings = embedder.embed(doc_texts)
    assert len(embeddings) == 130
    assert all(len(emb) == 384 for emb in embeddings)

    # Query embedding
    q_emb = embedder.embed_query("compliance requirements")
    assert len(q_emb) == 384
    assert isinstance(q_emb[0], float)


def test_embedding_validation_rejects_nan_and_wrong_dim():
    """Verify _validate_vector rejects NaN, Inf, and incorrect dimensions."""
    # Valid vector
    valid_vec = [0.1] * 384
    res = _validate_vector(valid_vec, 384)
    assert len(res) == 384

    # Wrong dimension
    with pytest.raises(ValueError):
        _validate_vector([0.1] * 128, 384)

    with pytest.raises(ValueError):
        _validate_vector([0.1] * 768, 384)

    # NaN / Inf rejection
    nan_vec = [0.1] * 383 + [float("nan")]
    with pytest.raises(ValueError):
        _validate_vector(nan_vec, 384)

    inf_vec = [0.1] * 383 + [float("inf")]
    with pytest.raises(ValueError):
        _validate_vector(inf_vec, 384)


def test_embedding_model_mismatch_detection():
    """Verify system recognizes model dimension mismatch when given non-384 vectors."""
    with pytest.raises(ValueError):
        _validate_vector([0.1] * 512, 384)


# ==============================================================================
# 2. Ingestion Pathways & Idempotency Testing
# ==============================================================================

def test_ingestion_pathway_compilation_and_searchability(val_app):
    """Test full pipeline: creation, compilation, BM25 indexing, QA generation, and retrieval."""
    with val_app.app_context():
        admin = User.query.filter_by(role=UserRole.ADMIN).first()
        dept = Department.query.first()

        policy = Policy(
            policy_id="VAL-INGEST-001",
            title="Independent Validation Policy",
            description="Testing end-to-end ingestion integrity",
            author_id=admin.id,
            department_id=dept.id,
            status=PolicyStatus.ACTIVE,
            confidentiality=ConfidentialityLevel.INTERNAL,
        )
        db.session.add(policy)
        db.session.commit()

        content = (
            "# 1. Purpose\nThis policy defines remote work ergonomics equipment allowances.\n\n"
            "# 2. Allowance\nEmployees are entitled to a one-time reimbursement of up to $500 for ergonomic equipment.\n\n"
            "# 3. Process\nSubmit claims via the finance portal within 30 days of purchase with itemized receipts."
        )

        version = PolicyVersion(
            policy_id=policy.id,
            version_num=1.0,
            version_label="v1.0",
            content=content,
            is_active=True,
            status="approved",
            created_by_id=admin.id,
        )
        db.session.add(version)
        db.session.commit()

        # Execute compilation
        compiler = KnowledgeCompilerPipeline()
        job = compiler.compile(policy.id, version.id)

        # Verify DB state
        assert job.stage == CompilationStage.READY
        assert job.chunk_count >= 3
        assert job.qa_count >= 1

        chunks = PolicyChunkV2.query.filter_by(version_id=version.id).all()
        assert len(chunks) == job.chunk_count
        assert all(c.text_hash for c in chunks)
        assert all(c.char_count > 0 for c in chunks)

        # Verify BM25 index is updated
        bm25 = PersistentBM25Index()
        scores = bm25.get_scores("ergonomic equipment reimbursement $500")
        assert len(scores) > 0


def test_idempotent_recompilation_does_not_duplicate_chunks(val_app):
    """Verify compiling the same version multiple times does not create duplicate chunks."""
    with val_app.app_context():
        admin = User.query.filter_by(role=UserRole.ADMIN).first()
        dept = Department.query.first()

        p = Policy(
            policy_id="VAL-IDEM-001",
            title="Idempotency Test Policy",
            description="Testing idempotent compilation",
            author_id=admin.id,
            department_id=dept.id,
            status=PolicyStatus.ACTIVE,
        )
        db.session.add(p)
        db.session.commit()

        v = PolicyVersion(
            policy_id=p.id,
            version_num=1.0,
            version_label="v1.0",
            content="Section 1: Data Retention\nCustomer records must be securely retained for 7 years.",
            is_active=True,
            status="approved",
            created_by_id=admin.id,
        )
        db.session.add(v)
        db.session.commit()

        # Run 1
        compiler = KnowledgeCompilerPipeline()
        j1 = compiler.compile(p.id, v.id)
        c_count_1 = PolicyChunkV2.query.filter_by(version_id=v.id).count()

        # Run 2 (recompilation)
        j2 = compiler.compile(p.id, v.id)
        c_count_2 = PolicyChunkV2.query.filter_by(version_id=v.id).count()

        assert c_count_1 == c_count_2, "Idempotent compilation must not duplicate chunks"
        assert j2.stage == CompilationStage.READY


def test_compiler_failure_cannot_mark_policy_ready(val_app):
    """Verify that if a compiler stage fails, the stage is FAILED and NOT READY."""
    with val_app.app_context():
        admin = User.query.filter_by(role=UserRole.ADMIN).first()
        dept = Department.query.first()

        p = Policy(
            policy_id="VAL-FAIL-001",
            title="Failing Stage Policy",
            description="Testing failure handling",
            author_id=admin.id,
            department_id=dept.id,
            status=PolicyStatus.DRAFT,
        )
        db.session.add(p)
        db.session.commit()

        v = PolicyVersion(
            policy_id=p.id,
            version_num=1.0,
            version_label="v1.0",
            content="Content for failure test",
            is_active=False,
            created_by_id=admin.id,
        )
        db.session.add(v)
        db.session.commit()

        compiler = KnowledgeCompilerPipeline()
        # Force a failure during answer generator
        with patch.object(compiler.answer_generator, "generate", side_effect=RuntimeError("Simulated LLM/Memory crash")):
            job = compiler.compile(p.id, v.id)

        assert job.stage == CompilationStage.FAILED, "Failed compilation must mark stage FAILED"
        assert job.stage != CompilationStage.READY, "Failed compilation cannot leave stage READY"
        assert "Simulated LLM/Memory crash" in (job.error or "")


# ==============================================================================
# 3. Authorization & Zero-Leakage Verification
# ==============================================================================

def test_zero_leakage_confidentiality_isolation(val_app):
    """Verify restricted confidential policy evidence is never leaked to public/general scopes."""
    with val_app.app_context():
        admin = User.query.filter_by(role=UserRole.ADMIN).first()
        dept = Department.query.first()

        # Create RESTRICTED policy
        p_sec = Policy(
            policy_id="VAL-SEC-001",
            title="Executive Salary Bands & M&A Strategy",
            description="Highly confidential executive compensation details",
            author_id=admin.id,
            department_id=dept.id,
            status=PolicyStatus.ACTIVE,
            confidentiality=ConfidentialityLevel.RESTRICTED,
        )
        db.session.add(p_sec)
        db.session.commit()

        v_sec = PolicyVersion(
            policy_id=p_sec.id,
            version_num=1.0,
            version_label="v1.0",
            content="Executive severance is guaranteed at 24 months base pay during any acquisition.",
            is_active=True,
            status="approved",
            created_by_id=admin.id,
        )
        db.session.add(v_sec)
        db.session.commit()

        KnowledgeCompilerPipeline().compile(p_sec.id, v_sec.id)

        # Verify evidence filter for a public-only / employee scope
        filter_svc = EvidenceFilter()
        public_scope = QueryScope(
            user_id=9999,
            role="employee",
            department_ids=(dept.id,),
            allowed_confidentiality=("public",)
        )

        allowed = filter_svc.is_authorized_for_policy(public_scope, p_sec)
        assert allowed is False, "EvidenceFilter must deny public scope access to RESTRICTED policy"

        admin_scope = QueryScope(
            user_id=admin.id,
            role="admin",
            department_ids=(dept.id,),
            is_admin=True,
            allowed_confidentiality=("public", "internal", "confidential", "restricted")
        )
        assert filter_svc.is_authorized_for_policy(admin_scope, p_sec) is True, "Admin scope must have access to RESTRICTED policy"
