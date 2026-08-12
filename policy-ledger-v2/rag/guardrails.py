"""
rag/guardrails.py
Configurable guardrails for input and output processing.
"""
import re

# Configuration
GUARDRAILS_CONFIG = {
    "INPUT_BLOCK_OUT_OF_SCOPE": True,
    "OUTPUT_CHECK_CITATIONS": True,
    "OUTPUT_BLOCK_TOXICITY": True,
    "OUTPUT_REDACT_PII": True,
}

# Regex patterns for lightweight classification
OUT_OF_SCOPE_PATTERNS = [
    re.compile(r"\b(legal advice|sue|lawsuit|attorney)\b", re.IGNORECASE),
    re.compile(r"\b(medical advice|diagnose|prescription|symptoms)\b", re.IGNORECASE),
    re.compile(r"\b(fire|terminate|justify firing|let go)\b", re.IGNORECASE),
]

# Simple PII patterns
PII_PATTERNS = [
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED_SSN]"),
    (re.compile(r"\b[\w\.-]+@[\w\.-]+\.\w+\b"), "[REDACTED_EMAIL]"),
    (re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"), "[REDACTED_PHONE]"),
]

def check_input_guardrails(query: str) -> tuple[bool, str]:
    """
    Check if the input query is allowed.
    Returns (is_allowed, reason_or_fallback_message).
    """
    if not GUARDRAILS_CONFIG["INPUT_BLOCK_OUT_OF_SCOPE"]:
        return True, ""
        
    for pattern in OUT_OF_SCOPE_PATTERNS:
        if pattern.search(query):
            return False, "This assistant can answer questions about company policy text but can't provide legal/HR advice on individual cases — please contact HR directly."
            
    return True, ""


def apply_output_guardrails(text: str, retrieved_chunk_ids: list[str]) -> str:
    """
    Applies output guardrails like PII redaction and citation checking.
    """
    if not text:
        return text
        
    # 1. PII Redaction
    if GUARDRAILS_CONFIG["OUTPUT_REDACT_PII"]:
        for pattern, replacement in PII_PATTERNS:
            text = pattern.sub(replacement, text)
            
    # 2. Citation check (simplified)
    # Ensure every citation bracket [Policy: ..., Section: ...] maps to a chunk ID.
    # If OUTPUT_CHECK_CITATIONS is True, we could enforce logic here, but returning the text for now.
    
    # 3. Toxicity check (simplified)
    if GUARDRAILS_CONFIG["OUTPUT_BLOCK_TOXICITY"]:
        toxic_words = ["stupid", "idiot", "dumb"]
        if any(w in text.lower() for w in toxic_words):
            return "The generated response was blocked by safety filters."

    return text

def apply_document_pii_redaction(text: str) -> str:
    """
    Redact PII before documents enter the vector store.
    """
    # Use the same PII patterns as output
    for pattern, replacement in PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text
