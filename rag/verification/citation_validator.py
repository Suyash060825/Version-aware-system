"""
rag/verification/citation_validator.py
Validates and enriches citations against authoritative database records.
Rejects unresolvable citations, never fabricates IDs, and ensures strict traceability.
"""
from typing import List, Dict, Any, Optional
from models import db, Policy, PolicyVersion, PolicyChunkV2
from rag.authorization.evidence_filter import get_evidence_filter

class CitationValidator:
    def __init__(self):
        pass

    def validate_and_enrich(self, raw_citations: List[Dict[str, Any]], scope: Optional[Any] = None) -> List[Dict[str, Any]]:
        """
        Validate and enrich citation list with authoritative database records.
        Strict invariant: Every citation MUST resolve to an actual Policy and PolicyVersion,
        and must be authorized for the user scope when scope is provided.
        Invalid, fabricated, or inaccessible records are dropped.
        """
        if not raw_citations:
            return []

        evidence_filter = get_evidence_filter()

        validated = []
        seen = set()

        # Batch pre-fetch chunk, policy, and version records in single queries (eliminates N+1 lookups)
        c_ids = [c.get("chunk_id") for c in raw_citations if c.get("chunk_id")]
        chunks_map = {}
        if c_ids:
            try:
                chunks_map = {chk.chunk_id: chk for chk in PolicyChunkV2.query.filter(PolicyChunkV2.chunk_id.in_(c_ids)).all()}
            except Exception:
                chunks_map = {}

        p_ids = set()
        v_ids = set()
        for cit in raw_citations:
            cid = cit.get("chunk_id")
            if cid in chunks_map:
                p_ids.add(chunks_map[cid].policy_id)
                v_ids.add(chunks_map[cid].version_id)
            pid = cit.get("policy_id")
            if pid:
                try:
                    p_ids.add(int(pid))
                except (ValueError, TypeError):
                    pass
            vid = cit.get("version_id")
            if vid:
                try:
                    v_ids.add(int(vid))
                except (ValueError, TypeError):
                    pass

        policies_map = {}
        if p_ids:
            try:
                policies_map = {p.id: p for p in Policy.query.filter(Policy.id.in_(p_ids)).all()}
            except Exception:
                policies_map = {}

        versions_map = {}
        if v_ids:
            try:
                versions_map = {v.id: v for v in PolicyVersion.query.filter(PolicyVersion.id.in_(v_ids)).all()}
            except Exception:
                versions_map = {}

        for cit in raw_citations:
            policy_id = cit.get("policy_id")
            version_id = cit.get("version_id")
            chunk_id = cit.get("chunk_id")

            policy = None
            version = None

            # 1. Resolve via chunk_id if available (using batch pre-fetch first)
            if chunk_id:
                chunk = chunks_map.get(chunk_id)
                if not chunk:
                    chunk = PolicyChunkV2.query.filter_by(chunk_id=chunk_id).first()
                if chunk:
                    policy = policies_map.get(chunk.policy_id) or db.session.get(Policy, chunk.policy_id)
                    version = versions_map.get(chunk.version_id) or db.session.get(PolicyVersion, chunk.version_id)
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
                    p_int = int(policy_id)
                    policy = policies_map.get(p_int) or db.session.get(Policy, p_int)
                except (ValueError, TypeError):
                    pass

            # 3. Resolve via policy_name search if still not found
            if not policy and cit.get("policy_name") and cit.get("policy_name") not in ("Policy", "N/A", "Unknown"):
                p_name = cit["policy_name"].strip()
                if len(p_name) > 5 and p_name.lower() not in ("policy", "internal", "guidelines", "general", "company"):
                    policy = Policy.query.filter(Policy.title == p_name).first()
                    if not policy:
                        policy = Policy.query.filter(Policy.title.ilike(p_name)).first()

            # 4. Resolve version
            if policy and not version:
                if version_id:
                    try:
                        v_int = int(version_id)
                        version = versions_map.get(v_int) or db.session.get(PolicyVersion, v_int)
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

            # DEFENSE-IN-DEPTH REQUIREMENT 7: Verify user scope is authorized for the cited policy
            if scope is not None and not evidence_filter.is_authorized_for_policy(scope, policy):
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

    def enrich_only(self, citations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Zero-DB enrichment for fast-path exits (L0, L1, L3) that already verified
        and resolved policies, versions, chunks, and authorization.
        Deduplicates and standardizes citation display fields.
        """
        if not citations:
            return []

        enriched = []
        seen = set()

        for cit in citations:
            p_id = cit.get("policy_id")
            v_id = cit.get("version_id")
            if not p_id or not v_id:
                continue

            section = cit.get("section") or "General"
            page_val = cit.get("page", 1)
            page_int = int(page_val) if str(page_val).isdigit() else 1
            ver_str = str(cit.get("version", "1.0"))

            key = (int(p_id), int(v_id), section, page_int)
            if key in seen:
                continue
            seen.add(key)

            enriched.append({
                "policy_id": int(p_id),
                "version_id": int(v_id),
                "policy_name": cit.get("policy_name") or "Policy",
                "version": ver_str,
                "section": section,
                "page": page_int,
                "chunk_id": cit.get("chunk_id")
            })

        return enriched
