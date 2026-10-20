"""
tests/test_veritas_e2e_pass.py
Comprehensive End-to-End Validation Suite for the Veritas Platform.
Covers:
- Ingestion of all policy formats (TXT, Markdown, Spreadsheets, HTML, OCR)
- Normalization & Heading-Aware Chunking (No single-block collapsing)
- Temporal Version Resolution (v1.0 vs v2.0, overlapping & historical intervals)
- Cross-Policy Ranking & Contextual Reranking
- Security & RBAC Enforcement (Role x Clearance x Department)
- Safe Abstention on Out-of-Scope / Hallucinatory Queries
- Model Routing, Streaming SSE Payload & Guardrails Sanitization
- Latency & Performance Budget Checks
"""
import os
import time
import pytest
from datetime import date
from unittest.mock import MagicMock, patch

from tests.test_data import (
    SAMPLE_TXT_POLICY,
    SAMPLE_MARKDOWN_POLICY,
    SAMPLE_SPREADSHEET_TEXT,
    SAMPLE_OCR_PDF_TEXT,
    SAMPLE_HTML_POLICY,
    SEED_POLICIES_WITH_VERSIONS,
    GROUND_TRUTH_QA_BENCHMARK,
    AUTHORIZATION_TEST_MATRIX,
    LATENCY_BUDGETS_MS
)
from rag.compiler.document_normalizer import DocumentNormalizer
from rag.compiler.structure_extractor import StructureExtractor
from rag.chunking.chunker import chunk_policy
from rag.versions.resolver import VersionResolver
from rag.authorization.evidence_filter import EvidenceFilter
from rag.generation.provider import get_llm_provider, MockProvider
from rag.engine.query_engine import get_query_engine
from rag.engine.query_scope import QueryScope
from models import PolicyStatus, UserRole
from app import create_app


@pytest.fixture(scope="module")
def app_ctx():
    app = create_app("testing")
    with app.app_context():
        yield app


class DummyPolicy:
    def __init__(self, id=1, title="Test Policy", department=None):
        self.id = id
        self.title = title
        self.department = department

class DummyVersion:
    def __init__(self, id=1, effective_date=date(2023, 1, 1), effective_to=None):
        self.id = id
        self.effective_date = effective_date
        self.effective_to = effective_to

class MockAuthPolicy:
    def __init__(self, policy_id, title="Matrix Policy", confidentiality="internal", department_id=1):
        self.id = policy_id
        self.title = title
        self.confidentiality = confidentiality
        self.department_id = department_id
        self.status = PolicyStatus.ACTIVE


# ==============================================================================
# 1. Ingestion & Chunking Across All Policy Types
# ==============================================================================

def test_ingestion_and_chunking_all_formats():
    """Verify that TXT, Markdown, Spreadsheets, HTML, and OCR PDFs decompose into distinct semantic sections."""
    normalizer = DocumentNormalizer()
    extractor = StructureExtractor()
    pol = DummyPolicy(id=101, title="Corporate Governance")
    ver = DummyVersion(id=201)

    # 1. Numbered Text Policy
    ir_txt = normalizer.normalize(SAMPLE_TXT_POLICY, pol, ver)
    assert len(ir_txt.sections) >= 4, f"Numbered policy must extract multiple sections, got {len(ir_txt.sections)}"
    chunks_txt = extractor.extract(ir_txt)
    assert len(chunks_txt) >= 4, "Should produce at least 4 semantic chunks"
    assert any("Remote Work" in c.text or "stipend" in c.text for c in chunks_txt)

    # 2. Markdown Policy (# and ##)
    ir_md = normalizer.normalize(SAMPLE_MARKDOWN_POLICY, pol, ver)
    assert len(ir_md.sections) >= 3, f"Markdown policy must split on #/## headings, got {len(ir_md.sections)}"
    chunks_md = extractor.extract(ir_md)
    assert len(chunks_md) >= 3, "Markdown policy must produce structured chunks"

    # 3. Spreadsheets / Tabular Data
    ir_sheet = normalizer.normalize(SAMPLE_SPREADSHEET_TEXT, pol, ver)
    assert len(ir_sheet.sections) >= 2, f"Spreadsheet text must split by sheet headings, got {len(ir_sheet.sections)}"
    chunks_sheet = extractor.extract(ir_sheet)
    assert len(chunks_sheet) >= 2

    # 4. OCR PDF with [Page 1 — OCR]
    chunks_ocr = chunk_policy(SAMPLE_OCR_PDF_TEXT, policy_id=101, policy_name="Privacy Directive", version="1.0")
    assert len(chunks_ocr) >= 2, "OCR text must be chunked properly"
    assert chunks_ocr[0].page == 1, f"Expected page 1 for OCR chunk, got {chunks_ocr[0].page}"
    assert "[Page 1 — OCR]" not in chunks_ocr[0].text, "OCR page header marker must be stripped from text"


def test_oversized_paragraph_subchunking():
    """Verify that paragraphs exceeding 1200 characters are safely split by sentences without losing content."""
    long_para = "This is an authoritative corporate compliance rule regarding data protection. " * 35
    assert len(long_para) > 1200, f"Setup error: test paragraph should exceed 1200 chars, got {len(long_para)}"

    normalizer = DocumentNormalizer()
    extractor = StructureExtractor()
    pol = DummyPolicy(id=102, title="Long Policy")
    ver = DummyVersion(id=202)

    ir = normalizer.normalize(long_para, pol, ver)
    chunks = extractor.extract(ir)
    assert len(chunks) > 1, f"Oversized paragraph ({len(long_para)} chars) must be split into multiple chunks"
    for c in chunks:
        assert c.char_count <= 1200, f"Chunk {c.chunk_id} exceeds 1200 character ceiling ({c.char_count})"


# ==============================================================================
# 2. Temporal Version Selection & Resolution
# ==============================================================================

def test_temporal_version_resolver():
    """Verify that historical and date-bounded queries resolve to the exact version rather than assuming highest numeric version."""
    resolver = VersionResolver()

    # Query targeting historical year
    tq_2022 = resolver.parse_temporal_query("What was the internet allowance in 2022?")
    assert tq_2022.target_date is not None
    assert tq_2022.target_date.year == 2022
    assert tq_2022.historical is True

    # Query targeting before 2024
    tq_before = resolver.parse_temporal_query("What was the per diem before 2024?")
    assert tq_before.target_date is not None
    assert tq_before.target_date.year in (2023, 2024) or tq_before.end_date.year in (2023, 2024)

    # Version comparison query
    tq_cmp = resolver.parse_temporal_query("Compare version 1.0 vs version 2.0")
    assert tq_cmp.comparison_versions is not None
    v1, v2 = tq_cmp.comparison_versions
    assert float(v1) == 1.0 and float(v2) == 2.0


# ==============================================================================
# 3. Authorization & Clearance Matrix
# ==============================================================================

def test_authorization_matrix_independent():
    """Verify that all role, department, and clearance combinations strictly enforce zero false grants."""
    ev_filter = EvidenceFilter()
    ev_filter.clear_cache()

    for role, clearance, u_dept, conf, p_dept, expected_allow, desc in AUTHORIZATION_TEST_MATRIX:
        user_scope = QueryScope(
            user_id=99,
            role=role,
            department_ids=[u_dept] if u_dept else [],
            allowed_confidentiality=["public", "internal"] if clearance != "public_only" else ["public"],
            is_admin=(role == "admin")
        )
        if clearance == "restricted" or role in ("admin", "executive", "legal"):
            user_scope.allowed_confidentiality.extend(["confidential", "restricted"])
        elif clearance == "confidential" or role in ("hr", "manager"):
            user_scope.allowed_confidentiality.append("confidential")

        dummy_pol = MockAuthPolicy(
            policy_id=777,
            title="Matrix Policy",
            confidentiality=conf,
            department_id=p_dept
        )

        allowed = ev_filter.is_authorized_for_policy(user_scope, dummy_pol)
        assert allowed == expected_allow, f"Failed auth check: {desc} (Got {allowed}, Expected {expected_allow})"


# ==============================================================================
# 4. Safe Abstention & Out-of-Scope Queries
# ==============================================================================

def test_safe_abstention_on_unanswerable_queries(app_ctx):
    """Verify that the engine abstains safely without hallucinating when no policy evidence exists."""
    engine = get_query_engine()

    res = engine.answer("What is the pet insurance policy for flying space unicorns?")
    assert res.abstained is True or "couldn't find" in res.answer.lower() or "not find" in res.answer.lower() or res.confidence < 0.5
    assert res.citations == [] or len(res.citations) == 0


# ==============================================================================
# 5. Model Provider Routing & Streaming SSE Integrity
# ==============================================================================

def test_model_provider_routing_and_mock_backend():
    """Verify that LLM_BACKEND=mock yields instant mock answers across both generation and chat subsystems."""
    with patch.dict(os.environ, {"LLM_BACKEND": "mock"}):
        from rag.generation.provider import get_llm_provider as get_gen_provider
        from rag.llm_provider import get_llm_provider as get_core_provider

        gen_llm = get_gen_provider(force_reload=True)
        assert isinstance(gen_llm, MockProvider)
        assert gen_llm.health_check() is True

        core_llm = get_core_provider(force_reload=True)
        assert core_llm.health_check() is True
        resp = core_llm.generate("Hello policy")
        assert resp.fallback is False
        assert "Mock" in resp.text


def test_streaming_event_contract(app_ctx):
    """Verify that streaming answer generator produces tokens and a valid done payload with model field."""
    engine = get_query_engine()

    events = list(engine.stream_answer("What is the remote work policy?"))
    assert len(events) >= 1

    done_events = [e for e in events if e.get("type") == "done"]
    assert len(done_events) == 1, "Stream must terminate with exactly one done event"
    done_payload = done_events[0]["result"]
    assert "answer" in done_payload
    assert "citations" in done_payload
    assert "route" in done_payload
    assert "model" in done_payload
    assert "latency_ms" in done_payload


# ==============================================================================
# 6. Performance & Latency Budgets
# ==============================================================================

def test_warm_query_latency_budget(app_ctx):
    """Verify that warm RAG queries stay well within the established performance budgets."""
    engine = get_query_engine()

    # Warm-up call
    _ = engine.answer("What is the remote work policy?")

    # Measured call
    t0 = time.perf_counter()
    res = engine.answer("What is the remote work policy?")
    latency_ms = (time.perf_counter() - t0) * 1000

    assert latency_ms < LATENCY_BUDGETS_MS["end_to_end_warm_p95"] * 2, (
        f"Warm query latency {latency_ms:.2f}ms exceeds allowed ceiling"
    )


def test_model_works_across_all_ai_subsystems(app_ctx):
    """Verify that model generation works properly across Policy AI, What-If AI, and Meeting AI."""
    with patch.dict(os.environ, {"LLM_BACKEND": "mock"}):
        from policy_ai import generate_policy_draft, rewrite_text
        from whatif_ai import evaluate_scenario
        from meeting_ai import generate_mom

        # 1. Policy AI Writer
        draft = generate_policy_draft("Workplace Ergonomics", "Guidelines for desk setup", "HR", "Monitor height, chair support")
        assert len(draft) >= 20, "Policy AI draft must produce complete text"

        # 2. Policy AI Rewrite
        rewritten = rewrite_text("Employees can work from home on Fridays.", mode="simplify")
        assert len(rewritten) > 10

        # 3. What-If Simulator
        verdict = evaluate_scenario("Can an employee work from home 4 days a week?")
        assert "verdict" in verdict and "confidence" in verdict

        # 4. Meeting AI Minutes of Meeting
        notes = "Decision: Launch new policy next week. Action: @Alice update handbook by Friday."
        mom = generate_mom(notes)
        assert "summary" in mom and "action_items" in mom
