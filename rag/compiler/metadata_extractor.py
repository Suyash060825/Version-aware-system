"""
rag/compiler/metadata_extractor.py
Extracts administrative, organizational, and regulatory metadata from document headers and text.
"""
import re
from datetime import datetime, date
from typing import Dict, Any, Optional
from rag.compiler.document_ir import DocumentIR

class MetadataExtractor:
    CONFIDENTIALITY_PATTERNS = [
        (r"\b(?:strictly confidential|restricted)\b", "restricted"),
        (r"\b(?:confidential|internal only|proprietary)\b", "confidential"),
        (r"\b(?:internal use|internal)\b", "internal"),
        (r"\b(?:public|unclassified)\b", "public"),
    ]

    DEPARTMENT_PATTERNS = [
        (r"\b(?:human resources|hr department|people ops)\b", "Human Resources"),
        (r"\b(?:information technology|it department|security ops)\b", "Information Technology"),
        (r"\b(?:finance|accounting|treasury)\b", "Finance"),
        (r"\b(?:legal|compliance|general counsel)\b", "Legal & Compliance"),
        (r"\b(?:engineering|software engineering|r&d)\b", "Engineering"),
        (r"\b(?:operations|facilities|administration)\b", "Operations"),
    ]

    DATE_PATTERNS = [
        r"effective\s*(?:date|from)?[:\s]+([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4}|[A-Za-z]+\s+[0-9]{1,2},?\s+[0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2})",
        r"published\s*date[:\s]+([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4}|[A-Za-z]+\s+[0-9]{1,2},?\s+[0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2})",
    ]

    def extract(self, doc_ir: DocumentIR) -> Dict[str, Any]:
        text_sample = "\n".join([s.title + " " + s.content for s in doc_ir.sections[:5]]) if doc_ir.sections else ""
        metadata: Dict[str, Any] = {
            "department": doc_ir.department,
            "policy_type": doc_ir.policy_type or "General Policy",
            "confidentiality": "internal",
            "applicable_roles": ["All Employees"],
            "effective_from": doc_ir.effective_from,
            "effective_to": doc_ir.effective_to,
            "approval_authority": None,
            "policy_owner": None,
        }

        # Confidentiality
        for pattern, level in self.CONFIDENTIALITY_PATTERNS:
            if re.search(pattern, text_sample, re.I):
                metadata["confidentiality"] = level
                break

        # Department if not set on IR
        if not metadata["department"]:
            for pattern, dept_name in self.DEPARTMENT_PATTERNS:
                if re.search(pattern, text_sample, re.I):
                    metadata["department"] = dept_name
                    break

        # Roles
        if re.search(r"\b(?:all employees|all staff|company wide|all personnel)\b", text_sample, re.I):
            metadata["applicable_roles"] = ["All Employees"]
        elif re.search(r"\b(?:managers?|supervisors?|leads?)\b", text_sample, re.I):
            metadata["applicable_roles"] = ["Managers", "HR", "Leadership"]
        elif re.search(r"\b(?:executives?|c-suite|directors?)\b", text_sample, re.I):
            metadata["applicable_roles"] = ["Executives", "Directors"]

        # Effective date extraction if missing
        if not metadata["effective_from"]:
            for pattern in self.DATE_PATTERNS:
                match = re.search(pattern, text_sample, re.I)
                if match:
                    metadata["effective_from_raw"] = match.group(1)
                    break

        return metadata
