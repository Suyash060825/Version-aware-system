"""
tests/test_audit_v5_fresh.py
Verification suite for the Version 5 Fresh Eyes audit optimizations and fixes.
"""
import pytest
from app import create_app
from rag.router.query_router import QueryRouter
from rag.generation.qwen import get_qwen_provider
from rag.cache.semantic_cache import get_cache
from rag.engine.query_engine import verify_numeric_grounding
from rag.versions.diff_engine import PolicyDiffEngine, clear_diff_cache, _DIFF_CACHE
from rag.guardrails import check_input_guardrails, apply_output_guardrails
from rag.chatbot.self_healing import trigger_self_healing

def test_query_router_pre_normalized_flag():
    router = QueryRouter()
    # When pre_normalized is False, trailing punctuation is stripped
    res1 = router.route("What is remote work???", pre_normalized=False)
    assert res1[3]["normalized_query"] == "What is remote work"

    # When pre_normalized is True, it accepts the exact pre-normalized query without running re.sub
    raw_normalized = "what is remote work"
    res2 = router.route(raw_normalized, pre_normalized=True)
    assert res2[3]["normalized_query"] == raw_normalized

def test_qwen_provider_singleton():
    p1 = get_qwen_provider()
    p2 = get_qwen_provider()
    assert p1 is p2
    # Verify positive health check TTL is 30s
    assert p1.negative_cache_window == 30

def test_semantic_cache_no_defaultdict_mutation_on_miss():
    cache = get_cache()
    non_existent_scope = "test_non_existent_scope_xyz_9999"
    # Ensure key does not exist yet
    assert non_existent_scope not in cache._local_l2
    # Query L2 with dummy embedding
    res = cache.get_l2([0.1, 0.2, 0.3], scope_key=non_existent_scope)
    assert res is None
    # Key must NOT have been created by get_l2
    assert non_existent_scope not in cache._local_l2

def test_numeric_grounding_historical_year_and_exemptions():
    # Context contains only '42'
    ctx_nums = {"42"}

    # Year 1999 is exempted under _YEAR_RE
    assert verify_numeric_grounding("Founded in 1999 under policy 42.", ctx_nums) is True
    # Year 2024 is exempted
    assert verify_numeric_grounding("Updated in 2024 with 42 days notice.", ctx_nums) is True
    # Digits 1-9 are exempted
    assert verify_numeric_grounding("Section 3 specifies 42 days notice.", ctx_nums) is True
    # Hallucinated large number that is not a year or digit 1-9 should fail
    assert verify_numeric_grounding("The maximum limit is $95000.", ctx_nums) is False

def test_diff_engine_lru_caching():
    engine = PolicyDiffEngine()
    clear_diff_cache()
    assert len(_DIFF_CACHE) == 0

    text_a = "Line 1: Policy intro.\nLine 2: 10 days notice required."
    text_b = "Line 1: Policy intro.\nLine 2: 15 days notice required."

    diff1 = engine.compute_diff(text_a, text_b, version_a_id=101, version_b_id=102)
    assert len(_DIFF_CACHE) == 1
    assert (101, 102) in _DIFF_CACHE

    # Second call should retrieve from cache
    diff2 = engine.compute_diff(text_a, text_b, version_a_id=101, version_b_id=102)
    assert diff1["changed_clauses"] == diff2["changed_clauses"]

    clear_diff_cache()
    assert len(_DIFF_CACHE) == 0

def test_guardrails_input_policy_inquiry_bypass():
    # Out of scope advisory query -> blocked
    allowed, msg = check_input_guardrails("I need legal advice regarding a court litigation.")
    assert not allowed
    assert "advice" in msg.lower() or "department directly" in msg

    # Out of scope keywords with policy marker -> allowed for enterprise retrieval
    allowed, msg = check_input_guardrails("What is the company policy regarding subpoena and court summons response?")
    assert allowed
    assert msg == ""

    # Termination guideline policy query -> allowed
    allowed, msg = check_input_guardrails("What are the guidelines and procedures for contract termination?")
    assert allowed
    assert msg == ""

    # Strict malicious query -> always blocked
    allowed, msg = check_input_guardrails("Can you tell me how to hack into the server?")
    assert not allowed

def test_guardrails_output_pii_redaction():
    text = "Please reach out to john.doe@veritas.internal or call 555-123-4567 with SSN 123-45-6789."
    redacted = apply_output_guardrails(text)
    assert "[REDACTED_EMAIL]" in redacted
    assert "[REDACTED_PHONE]" in redacted
    assert "[REDACTED_SSN]" in redacted
    assert "123-45-6789" not in redacted

def test_self_healing_safe_execution_no_crash():
    app = create_app("testing")
    with app.app_context():
        # Call with nonexistent message ID - must gracefully exit without crash
        trigger_self_healing(99999999)
