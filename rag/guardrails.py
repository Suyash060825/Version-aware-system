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
    re.compile(r"\b(legal advice|sue|lawsuit|attorney|lawyer|court|subpoena|litigation)\b", re.IGNORECASE),
    re.compile(r"\b(medical advice|diagnose|prescription|symptoms|treatment|doctor's note)\b", re.IGNORECASE),
    re.compile(r"\b(fire|terminate|justify firing|let go|layoff|redundancy|severance negotiation)\b", re.IGNORECASE),
    re.compile(r"\b(hack|bypass|exploit|penetration test|breach)\b", re.IGNORECASE)
]

TOXICITY_PATTERNS = [
    re.compile(r"\b(stupid|idiot|dumb|moron|crazy|insane|retarded|bastard)\b", re.IGNORECASE),
    re.compile(r"\b(kill|murder|suicide|die|harm)\b", re.IGNORECASE)
]

# Expanded PII patterns
PII_PATTERNS = [
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED_SSN]"),
    (re.compile(r"\b[A-CEGHJ-PR-TW-Z]{1}[A-CEGHJ-NPR-TW-Z]{1}[0-9]{6}[A-D\s]\b", re.IGNORECASE), "[REDACTED_NINO]"),
    (re.compile(r"\b[\w\.-]+@[\w\.-]+\.\w+\b"), "[REDACTED_EMAIL]"),
    (re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"), "[REDACTED_PHONE]"),
    (re.compile(r"\b(?:\d[ -]*?){13,16}\b"), "[REDACTED_CREDIT_CARD]"),
    (re.compile(r"\bEMP-\d{5,8}\b", re.IGNORECASE), "[REDACTED_EMP_ID]"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[REDACTED_IP]")
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


def apply_output_guardrails(text: str, top_chunks: list[dict] = None, user_role: str = "employee") -> str:
    """
    Applies output guardrails like PII redaction and citation checking.
    """
    if not text:
        return text
        
    # 1. PII Redaction (HR and Admin should see PII, employees should not)
    if GUARDRAILS_CONFIG["OUTPUT_REDACT_PII"] and user_role not in ("hr", "admin"):
        for pattern, replacement in PII_PATTERNS:
            text = pattern.sub(replacement, text)
            
    # 2. Citation check
    if GUARDRAILS_CONFIG["OUTPUT_CHECK_CITATIONS"] and top_chunks:
        valid_policies = {(c.get("policy_name") or "").lower() for c in top_chunks}
        # Find all citations e.g., [Policy: Name, Section: Sec]
        citations = re.findall(r"\[Policy:\s*(.*?)(?:,\s*Section:.*?)?\]", text)
        for cited_policy in citations:
            if cited_policy.lower() not in valid_policies:
                # Flag hallucinated citation
                return "The generated response was blocked because it contained a hallucinated citation."
                
    # 3. Toxicity check
    if GUARDRAILS_CONFIG["OUTPUT_BLOCK_TOXICITY"]:
        for pattern in TOXICITY_PATTERNS:
            if pattern.search(text):
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
