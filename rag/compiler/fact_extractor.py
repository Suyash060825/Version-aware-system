import re
from typing import List
from models import PolicyFact, now_utc
from rag.compiler.document_ir import ChunkIR

FACT_PATTERNS = [
    # "employees are entitled to 30 days of annual leave"
    (r"(\d+)\s*(day|week|month|hour)s?\s*(?:of|per)\s*([\w\s]+)", "leave_entitlement"),
    # "maximum reimbursement of ₹75,000"
    (r"(?:maximum|limit|ceiling|up to)\s*(?:of\s*)?(?:₹|Rs\.?|INR|\$)?\s*([\d,]+)", "reimbursement_limit"),
    # "notice period of 2 months"
    (r"notice\s+period\s+(?:of\s+|is\s+)?(\d+)\s*(day|week|month)", "notice_period"),
]

class FactExtractor:
    def extract(self, chunks: List[ChunkIR]) -> List[PolicyFact]:
        facts = []
        for chunk in chunks:
            for pattern, predicate in FACT_PATTERNS:
                matches = re.finditer(pattern, chunk.text, re.IGNORECASE)
                for match in matches:
                    groups = match.groups()
                    if predicate == "leave_entitlement" and len(groups) >= 3:
                        value, unit, scope = groups[0], groups[1], groups[2]
                        facts.append(PolicyFact(
                            policy_id=chunk.policy_id,
                            version_id=chunk.version_id,
                            subject="employee",
                            predicate=predicate,
                            value=value,
                            unit=unit,
                            scope=scope.strip(),
                            source_chunk_id=chunk.chunk_id,
                            confidence=0.9,
                            created_at=now_utc()
                        ))
                    elif predicate == "notice_period" and len(groups) >= 2:
                        value, unit = groups[0], groups[1]
                        facts.append(PolicyFact(
                            policy_id=chunk.policy_id,
                            version_id=chunk.version_id,
                            subject="employee",
                            predicate=predicate,
                            value=value,
                            unit=unit,
                            scope="termination",
                            source_chunk_id=chunk.chunk_id,
                            confidence=0.9,
                            created_at=now_utc()
                        ))
                    elif predicate == "reimbursement_limit" and len(groups) >= 1:
                        value = groups[0]
                        facts.append(PolicyFact(
                            policy_id=chunk.policy_id,
                            version_id=chunk.version_id,
                            subject="expense",
                            predicate=predicate,
                            value=value,
                            unit="currency",
                            scope="general",
                            source_chunk_id=chunk.chunk_id,
                            confidence=0.9,
                            created_at=now_utc()
                        ))
        return facts
