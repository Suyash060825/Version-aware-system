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

# Explicit advisory/malicious intents that must always be blocked
_STRICT_ADVISORY_PATTERNS = [
    re.compile(r"\b(legal advice|sue (?:my|the|them)|file a lawsuit|hire (?:an? )?attorney|representation in court)\b", re.IGNORECASE),
    re.compile(r"\b(medical advice|diagnose me|prescribe|treat my symptoms)\b", re.IGNORECASE),
    re.compile(r"\b(how to hack|how to bypass|exploit vulnerability|breach security system)\b", re.IGNORECASE),
]

# Legitimate enterprise policy inquiry cues that permit policy exploration
_POLICY_INQUIRY_RE = re.compile(
    r"\b(policy|standard|guidelines?|clause|section|procedure|rule|requirement|what is|what does|how do we|are we allowed|entitled|can i|am i|will i|allowed to)\b",
    re.IGNORECASE
)

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
    (re.compile(r"(?<![vV\d\.])\b(?:\d{1,3}\.){3}\d{1,3}\b(?!\.\d)"), "[REDACTED_IP]")
]

def check_input_guardrails(query: str) -> tuple[bool, str]:
    """
    Check if the input query is allowed.
    Returns (is_allowed, reason_or_fallback_message).
    """
    if not GUARDRAILS_CONFIG["INPUT_BLOCK_OUT_OF_SCOPE"]:
        return True, ""
        
    for pattern in _STRICT_ADVISORY_PATTERNS:
        if pattern.search(query):
            return False, "This assistant can answer questions about company policy text but can't provide legal, medical, or security penetration advice — please consult the appropriate department directly."

    # If asking about company policy/standards/guidelines, allow legitimate enterprise queries
    if _POLICY_INQUIRY_RE.search(query):
        return True, ""

    for pattern in OUT_OF_SCOPE_PATTERNS:
        if pattern.search(query):
            return False, "This assistant can answer questions about company policy text but can't provide legal/HR advice on individual cases — please contact HR directly."
            
    return True, ""


def apply_output_guardrails(text: str, top_chunks: list[dict] = None) -> str:
    """
    Applies output guardrails like PII redaction and citation checking.
    """
    if not text:
        return text
        
    # 1. PII Redaction
    if GUARDRAILS_CONFIG["OUTPUT_REDACT_PII"]:
        for pattern, replacement in PII_PATTERNS:
            text = pattern.sub(replacement, text)
            
    # 2. Citation check
    if GUARDRAILS_CONFIG["OUTPUT_CHECK_CITATIONS"] and top_chunks:
        valid_policies = {
            (c.get("policy_name") or c.get("policy_title") or "").strip().lower()
            for c in top_chunks
        } - {""}
        # Find all citations e.g., [Policy: Name, Section: Sec]
        citations = re.findall(r"\[Policy:\s*(.*?)(?:,\s*Section:.*?)?\]", text)
        for cited_policy in citations:
            cited_clean = cited_policy.strip().lower()
            if not any(cited_clean in vp or vp in cited_clean for vp in valid_policies):
                # Sanitize the unverified citation tag rather than dropping the whole answer
                text = re.sub(r"\[Policy:\s*" + re.escape(cited_policy) + r"(?:,\s*Section:.*?)?\]", "[Policy: Unverified]", text)
                
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
