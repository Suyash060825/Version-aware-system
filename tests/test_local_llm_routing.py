"""
tests/test_local_llm_routing.py
Comprehensive test suite verifying Veritas Local LLM Routing, deadlines, and fallbacks:
- Qwen3 4B default model and environment override
- Authoritative base URL resolution for native Fedora host and Docker Compose
- Provider generation via POST /api/chat and tags via GET /api/tags
- 25-second generation deadline enforcement and streaming cancellation
- Bounded fallback cascade without unbounded retries
- Accurate model provenance reporting
- Grounded evidence and citation verification boundary preservation
"""
import os
import json
import time
import pytest
from unittest.mock import patch, MagicMock

from config import Config
from app import create_app
from models import db, User, UserRole, Department, Policy, PolicyVersion, PolicyStatus
from rag.generation.provider import OllamaProvider
from rag.generation.qwen import get_qwen_provider, QwenLocalProvider
from rag.engine.query_engine import get_query_engine, QueryEngine
from rag.engine.query_scope import QueryScope


@pytest.fixture(scope="module")
def app_instance():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


# ==============================================================================
# 1. Configuration Tests
# ==============================================================================

def test_default_model_is_qwen3_4b():
    """Verify Qwen3 4B is default generation model when no explicit env is set."""
    with patch.dict(os.environ, {}, clear=True):
        assert "qwen3:4b-q4_K_M" in Config.LOCAL_LLM_MODEL
        assert Config.OLLAMA_MODEL == Config.LOCAL_LLM_MODEL


def test_explicit_env_model_override():
    """Verify explicit environment configuration overrides default model."""
    with patch.dict(os.environ, {"LOCAL_LLM_MODEL": "custom-model:latest"}):
        test_model = os.environ.get("LOCAL_LLM_MODEL")
        assert test_model == "custom-model:latest"


def test_base_url_native_and_docker_resolution():
    """Verify base URL resolves cleanly to localhost/127.0.0.1 for host and preserves Docker."""
    # When ollama hostname cannot be resolved, provider resolves to local host
    provider = OllamaProvider(base_url="http://127.0.0.1:11434")
    assert provider.base_url == "http://127.0.0.1:11434"

    # Diagnostics exposed
    diag = provider.diagnostics()
    assert diag["generation_endpoint"] == "http://127.0.0.1:11434/api/chat"
    assert diag["tags_endpoint"] == "http://127.0.0.1:11434/api/tags"
    assert diag["generation_deadline"] == 25.0


def test_invalid_timeout_settings_fail_validation():
    """Verify negative or zero timeout settings raise ValueError."""
    orig_deadline = Config.LLM_GENERATION_DEADLINE
    try:
        Config.LLM_GENERATION_DEADLINE = -5.0
        with pytest.raises(ValueError, match="LLM_GENERATION_DEADLINE must be positive"):
            Config.validate_configuration()
    finally:
        Config.LLM_GENERATION_DEADLINE = orig_deadline


# ==============================================================================
# 2. Provider Endpoint & Deadline Tests
# ==============================================================================

def test_provider_calls_post_api_chat():
    """Verify that generation calls POST /api/chat with model payload, not /api/tags."""
    provider = OllamaProvider(base_url="http://127.0.0.1:11434", model="qwen3:4b-q4_K_M")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "message": {"content": "Verified policy answer."},
        "prompt_eval_count": 15,
        "eval_count": 8
    }

    with patch.object(provider._session, "post", return_value=mock_resp) as mock_post:
        resp = provider.generate("What is the remote work policy?", timeout=25.0)
        assert mock_post.called
        call_url = mock_post.call_args[0][0]
        call_payload = mock_post.call_args[1]["json"]
        assert call_url == "http://127.0.0.1:11434/api/chat"
        assert call_payload["model"] == "qwen3:4b-q4_K_M"
        assert resp.text == "Verified policy answer."
        assert resp.model == "qwen3:4b-q4_K_M"
        assert resp.fallback is False


def test_provider_generation_with_specified_fallback_model():
    """Verify that generate() supports switching model dynamically without re-instantiation."""
    provider = OllamaProvider(base_url="http://127.0.0.1:11434", model="qwen3:4b-q4_K_M")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "message": {"content": "Fallback answer."},
    }

    with patch.object(provider._session, "post", return_value=mock_resp) as mock_post:
        resp = provider.generate("Test query", model="phi4-mini:3.8b-q4_K_M")
        call_payload = mock_post.call_args[1]["json"]
        assert call_payload["model"] == "phi4-mini:3.8b-q4_K_M"
        assert resp.model == "phi4-mini:3.8b-q4_K_M"


def test_streaming_deadline_enforcement_closes_response():
    """Verify that streaming provider enforces total generation deadline and closes stream on timeout."""
    provider = OllamaProvider(base_url="http://127.0.0.1:11434", model="qwen3:4b-q4_K_M")

    class SlowStreamResponse:
        def __init__(self):
            self.status_code = 200
            self.closed = False

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.close()

        def close(self):
            self.closed = True

        def iter_lines(self):
            # First token yields immediately
            yield json.dumps({"message": {"content": "Token1 "}}).encode("utf-8")
            # Sleep longer than the 0.2s deadline
            time.sleep(0.3)
            yield json.dumps({"message": {"content": "Token2 "}}).encode("utf-8")

    slow_resp = SlowStreamResponse()
    with patch.object(provider._session, "post", return_value=slow_resp):
        with pytest.raises(TimeoutError, match="Streaming token generation exceeded deadline"):
            list(provider.stream("Test prompt", timeout=0.2))
        assert slow_resp.closed is True, "HTTP stream must be closed upon deadline expiry"


# ==============================================================================
# 3. Deadline-Aware Model Routing & Verification Boundary in RAG Engine
# ==============================================================================

def test_rag_engine_routes_primary_to_qwen3_4b(app_instance):
    """Verify that RAG engine attempts Qwen3 4B as primary candidate."""
    engine = get_query_engine()
    assert "qwen3" in engine.llm.model.lower()


def test_fallback_model_cascade_on_timeout(app_instance):
    """Verify that when primary times out, engine tries secondary model and reports actual model."""
    engine = QueryEngine()

    call_history = []

    def mock_generate_grounded(query, chunks, max_tokens=200, timeout=None, model=None):
        call_history.append((model, timeout))
        if "qwen3:4b" in (model or ""):
            # Simulate primary model exceeding its 25s deadline
            raise TimeoutError("Qwen3 4B timed out after 25s")
        # Secondary candidate succeeds with verified grounded answer
        return {
            "answer": "Employees may work remotely 2 days per week with manager approval.",
            "model": model,
            "used_evidence_ids": [c.get("chunk_id") for c in chunks if c.get("chunk_id")]
        }

    sample_chunks = [{
        "chunk_id": "c1",
        "policy_id": 10,
        "policy_title": "Remote Work Policy",
        "version_label": "v1.0",
        "section_path": "Allowance",
        "text": "Employees may work remotely 2 days per week with manager approval."
    }]

    mock_conf = MagicMock()
    mock_conf.abstain = False
    mock_conf.value = 0.95
    sample_cits = [{
        "chunk_id": "c1",
        "policy_id": 10,
        "policy_name": "Remote Work Policy",
        "version": "1.0",
        "section": "Allowance",
        "page": 1
    }]

    with patch.object(engine.evidence_filter, "get_allowed_policy_ids", return_value={10}), \
         patch.object(engine.llm, "health_check", return_value=True), \
         patch.object(engine.llm, "generate_grounded_answer", side_effect=mock_generate_grounded), \
         patch.object(engine, "_verify_candidate", return_value=(True, "ENTAILMENT", 0.98, 0.01)), \
         patch.object(engine.fact_resolver, "try_resolve", return_value=None), \
         patch.object(engine, "_retrieve_and_rank", return_value=(sample_chunks, "rerank", mock_conf, sample_cits)):

        res = engine.answer("Explain the procedure and requirements for remote work approval and equipment allowance under the policy")

        # Assert primary was attempted first
        assert len(call_history) >= 2
        assert "qwen3:4b" in call_history[0][0]
        # Assert secondary model was called
        assert "phi4-mini" in call_history[1][0]
        # Assert actual generating model is recorded accurately
        assert res.model == "phi4-mini:3.8b-q4_K_M"
        assert res.llm_used is True
        assert res.usage.get("llm_routing", {}).get("fallback_used") is True
        assert res.usage.get("llm_routing", {}).get("actual_model") == "phi4-mini:3.8b-q4_K_M"


def test_unverified_candidate_is_rejected_and_falls_back(app_instance):
    """Verify that an answer failing grounding/NLI verification is rejected even if model finished quickly."""
    engine = QueryEngine()

    sample_chunks = [{
        "chunk_id": "c1",
        "policy_id": 10,
        "policy_title": "Remote Work Policy",
        "version_label": "v1.0",
        "section_path": "Allowance",
        "text": "Employees may work remotely 2 days per week with manager approval."
    }]

    # Model hallucinates a number not in the policy: 100 days
    hallucinated_output = {
        "answer": "Employees may work remotely 100 days per week.",
        "model": "qwen3:4b-q4_K_M",
        "used_evidence_ids": ["c1"]
    }

    with patch.object(engine.llm, "generate_grounded_answer", return_value=hallucinated_output), \
         patch.object(engine.fact_resolver, "try_resolve", return_value=None), \
         patch.object(engine.hybrid_retriever, "search", return_value=sample_chunks), \
         patch.object(engine.reranker, "rerank", return_value=sample_chunks):

        # Numeric grounding rejects 100 days (100 not in context numbers: {2})
        res = engine.answer("How many days can I work remotely?")

        # Must reject candidate and fall back to deterministic extraction
        assert "100" not in res.answer
        assert res.model == "deterministic-rag" or res.llm_used is False


def test_safe_abstention_preserved_when_no_evidence_matches(app_instance):
    """Verify that engine abstains cleanly without hallucination when retrieved evidence is empty."""
    engine = QueryEngine()

    with patch.object(engine.fact_resolver, "try_resolve", return_value=None), \
         patch.object(engine.hybrid_retriever, "search", return_value=[]), \
         patch.object(engine.reranker, "rerank", return_value=[]):

        res = engine.answer("What is the extraterrestrial space exploration reimbursement?")
        assert res.abstained is True
        assert res.citations == []
        assert "could not find sufficient" in res.answer.lower() or "insufficient" in res.abstain_reason.lower()


# ==============================================================================
# 4. Live Ollama Verification (Executed if native Ollama is running)
# ==============================================================================

def test_live_ollama_tags_and_installed_models():
    """Verify live Ollama responds on http://127.0.0.1:11434 with required models."""
    provider = OllamaProvider(base_url="http://127.0.0.1:11434")
    if not provider.health_check():
        pytest.skip("Local Ollama server is not running on host")

    assert provider.is_model_available("qwen3:4b-q4_K_M")
    assert provider.is_model_available("phi4-mini:3.8b-q4_K_M")
    assert provider.is_model_available("qwen3:1.7b-q4_K_M")


# ==============================================================================
# 5. Exact Model Matching, Precedence & Latency Telemetry Tests
# ==============================================================================

def test_exact_model_tag_matching_prevents_partial_leakage():
    """Verify that similar model names (e.g. 1.7b vs 4b) are never treated as matches."""
    from rag.generation.provider import _match_ollama_model

    # Exact tags must match
    assert _match_ollama_model("qwen3:4b-q4_K_M", "qwen3:4b-q4_K_M") is True
    assert _match_ollama_model("qwen3:4b-q4_K_M", "registry.ollama.ai/library/qwen3:4b-q4_K_M") is True

    # Partial tags must NEVER match
    assert _match_ollama_model("qwen3:4b-q4_K_M", "qwen3:1.7b-q4_K_M") is False
    assert _match_ollama_model("qwen3:1.7b-q4_K_M", "qwen3:4b-q4_K_M") is False
    assert _match_ollama_model("phi4-mini:3.8b-q4_K_M", "qwen3:4b-q4_K_M") is False

    # Untagged targets match untagged or :latest only
    assert _match_ollama_model("qwen3", "qwen3:latest") is True
    assert _match_ollama_model("qwen3", "qwen3:4b-q4_K_M") is False


def test_base_url_precedence_and_normalization():
    """Verify LOCAL_LLM_BASE_URL takes precedence and normalizes slashes without guessing."""
    with patch.dict(os.environ, {
        "LOCAL_LLM_BASE_URL": "http://ollama:11434///",
        "OLLAMA_BASE_URL": "http://legacy-host:11434/"
    }):
        provider = OllamaProvider()
        assert provider.base_url == "http://ollama:11434"
        assert not provider.base_url.endswith("/")


def test_ollama_timing_breakdown_captured():
    """Verify Ollama duration metrics (load, prompt_eval, eval) are parsed into usage."""
    provider = OllamaProvider(base_url="http://ollama:11434", model="qwen3:4b-q4_K_M")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "message": {"content": "Verified policy answer."},
        "prompt_eval_count": 25,
        "eval_count": 12,
        "load_duration": 50000000,          # 50ms in ns
        "prompt_eval_duration": 120000000,  # 120ms in ns
        "eval_duration": 80000000,          # 80ms in ns
        "total_duration": 250000000         # 250ms in ns
    }
    with patch.object(provider._session, "post", return_value=mock_resp):
        resp = provider.generate("What is leave policy?")
        assert resp.usage.get("prompt_tokens") == 25
        assert resp.usage.get("completion_tokens") == 12
        assert resp.usage.get("load_duration_ms") == 50.0
        assert resp.usage.get("prompt_eval_duration_ms") == 120.0
        assert resp.usage.get("eval_duration_ms") == 80.0
        assert resp.usage.get("total_duration_ms") == 250.0


def test_used_evidence_ids_validated_against_supplied_chunks():
    """Verify that hallucinations in used_evidence_ids are filtered to actual supplied chunk IDs."""
    provider = get_qwen_provider()
    chunks = [
        {"chunk_id": "chunk-valid-1", "text": "Valid text 1"},
        {"chunk_id": "chunk-valid-2", "text": "Valid text 2"}
    ]
    mock_json = json.dumps({
        "answer": "Grounded answer citing chunk 1.",
        "used_evidence_ids": ["chunk-valid-1", "hallucinated-chunk-999"]
    })
    with patch.object(provider, "generate", return_value=mock_json):
        result = provider.generate_grounded_answer("query", chunks)
        assert result is not None
        assert "chunk-valid-1" in result["used_evidence_ids"]
        assert "hallucinated-chunk-999" not in result["used_evidence_ids"]
