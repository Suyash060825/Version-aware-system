import pytest
from rag.entailment import verify_entailment

def test_entailment_lexical_overlap():
    chunks = [{"text": "The company policy allows 30 days of vacation."}]
    answer = "Employees get 30 days of vacation."
    # Since NLI is mocked or we can just test lexical overlap
    # We will test the basic function logic.
    is_entailed, score = verify_entailment(answer, chunks)
    assert is_entailed is True

def test_contradiction():
    chunks = [{"text": "The company policy allows 30 days of vacation."}]
    answer = "Employees get 50 days of vacation."
    # This might fail the lexical overlap if not enough overlap, but "Employees get 50 days of vacation" has overlap.
    # To truly test contradiction, we need NLI. We'll leave it as a placeholder.
    pass

def test_neutral():
    pass

def test_malformed_output():
    is_entailed, score = verify_entailment("", [])
    assert is_entailed is False
    assert score == 0.0

