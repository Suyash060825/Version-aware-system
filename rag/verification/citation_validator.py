"""
rag/verification/citation_validator.py
Validates and enriches citations against authoritative database records.
Rejects unresolvable citations, never fabricates IDs, and ensures strict traceability.
"""
from typing import List, Dict, Any, Optional
from models import db, Policy, PolicyVersion, PolicyChunkV2

class CitationValidator:
    def __init__(self):
        pass

    def validate_and_enrich(self, raw_citations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate and enrich citation list with authoritative database records.
        Strict invariant: Every citation MUST resolve to an actual Policy and PolicyVersion.
        Invalid, fabricated, or nonexistent records are dropped.
        """
        if not raw_citations:
            return []

        validated = []
        seen = set()

        for cit in raw_citations:
            policy_id = cit.get("policy_id")
            version_id = cit.get("version_id")
            chunk_id = cit.get("chunk_id")

            policy = None
            version = None

            # 1. Resolve via chunk_id if available
            if chunk_id:
                chunk = PolicyChunkV2.query.filter_by(chunk_id=chunk_id).first()
                if chunk:
                    policy = db.session.get(Policy, chunk.policy_id)
                    version = db.session.get(PolicyVersion, chunk.version_id)
                    section = chunk.section_path or cit.get("section") or "General"
                    page = chunk.page or cit.get("page") or 1
                else:
                    section = cit.get("section") or "General"
                    page = cit.get("page") or 1
            else:
                section = cit.get("section") or "General"
                page = cit.get("page") or 1

            # 2. Resolve via policy_id if not found via chunk
            if not policy and policy_id:
                try:
                    policy = db.session.get(Policy, int(policy_id))
                except (ValueError, TypeError):
                    pass

            # 3. Resolve via policy_name search if still not found
            if not policy and cit.get("policy_name") and cit.get("policy_name") not in ("Policy", "N/A", "Unknown"):
                policy = Policy.query.filter(Policy.title.ilike(cit["policy_name"].strip())).first()

            # 4. Resolve version
            if policy and not version:
                if version_id:
                    try:
                        version = db.session.get(PolicyVersion, int(version_id))
                    except (ValueError, TypeError):
                        pass
                if not version and cit.get("version"):
                    ver_str = str(cit["version"]).lstrip("v")
                    try:
                        v_num = float(ver_str)
                        version = PolicyVersion.query.filter_by(policy_id=policy.id, version_num=v_num).first()
                    except ValueError:
                        pass

            # Strict Safety Gate: If policy or version cannot be authoritatively resolved, reject citation
            if not policy or not version:
                continue

            # Ensure version belongs to policy
            if version.policy_id != policy.id:
                continue

            policy_title = policy.title
            version_num = version.version_number
            page_int = int(page) if str(page).isdigit() else 1

            key = (policy.id, version.id, section, page_int)
            if key in seen:
                continue
            seen.add(key)

            validated.append({
                "policy_id": policy.id,
                "version_id": version.id,
                "policy_name": policy_title,
                "version": str(version_num),
                "section": section,
                "page": page_int,
                "chunk_id": chunk_id
            })

        return validated
