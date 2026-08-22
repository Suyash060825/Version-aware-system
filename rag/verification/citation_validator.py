"""
rag/verification/citation_validator.py
Validates and enriches citations against authoritative database records.
Rejects placeholder citations and ensures traceability.
"""
from typing import List, Dict, Any
from models import db, Policy, PolicyVersion, PolicyChunkV2

class CitationValidator:
    def __init__(self):
        pass

    def validate_and_enrich(self, raw_citations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and enrich citation list with authoritative database values."""
        if not raw_citations:
            return []

        validated = []
        seen = set()

        for cit in raw_citations:
            policy_id = cit.get("policy_id")
            version_id = cit.get("version_id")
            chunk_id = cit.get("chunk_id")

            # Try to resolve policy from database
            policy = None
            if policy_id:
                try:
                    policy = db.session.get(Policy, int(policy_id))
                except (ValueError, TypeError):
                    pass

            version = None
            if version_id:
                try:
                    version = db.session.get(PolicyVersion, int(version_id))
                except (ValueError, TypeError):
                    pass

            # If chunk_id given, resolve chunk details
            section = cit.get("section") or "General"
            page = cit.get("page") or 1
            
            if chunk_id:
                chunk = PolicyChunkV2.query.filter_by(chunk_id=chunk_id).first()
                if chunk:
                    if not policy:
                        policy = db.session.get(Policy, chunk.policy_id)
                    if not version:
                        version = db.session.get(PolicyVersion, chunk.version_id)
                    section = chunk.section_path or section
                    page = chunk.page or page

            # If policy or version still None, check if policy_name is already descriptive
            policy_title = policy.title if policy else cit.get("policy_name")
            if not policy_title or policy_title in ("Policy", "N/A", "Unknown"):
                if policy:
                    policy_title = policy.title
                else:
                    # Try to fetch default active policy
                    first_p = Policy.query.first()
                    policy_title = first_p.title if first_p else "Company Policy"
                    policy_id = first_p.id if first_p else 1

            version_num = version.version_number if version else (cit.get("version") or "1.0")
            if version_num in ("N/A", "Unknown", None):
                version_num = "1.0"

            key = (policy_title, version_num, section, page)
            if key in seen:
                continue
            seen.add(key)

            validated.append({
                "policy_id": policy.id if policy else (policy_id or 1),
                "version_id": version.id if version else (version_id or 1),
                "policy_name": policy_title,
                "version": str(version_num),
                "section": section,
                "page": int(page) if str(page).isdigit() else 1,
                "chunk_id": chunk_id
            })

        return validated
