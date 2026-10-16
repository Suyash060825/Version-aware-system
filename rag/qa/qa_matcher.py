"""
rag/qa/qa_matcher.py
Precomputed QA matcher returning validated answers with authoritative citations.
Strictly verifies that Policy, PolicyVersion, and Source Chunks exist in the database.
"""
from typing import List, Optional, Dict, Any
from models import db, CanonicalQuestion, CompiledAnswer, Policy, PolicyVersion, PolicyChunkV2
from rag.qa.qa_index import CanonicalQAIndex
from rag.authorization.evidence_filter import get_evidence_filter

class QAMatcher:
    def __init__(self):
        self.index = CanonicalQAIndex()

    def match(self, query: str, query_embedding: List[float], scope: Optional[Any] = None, threshold: float = 0.80) -> Optional[Dict[str, Any]]:
        results = self.index.search(query_embedding, top_k=2)
        if not results:
            return None

        score, answer_id, question_id = results[0][:3]
        meta = results[0][3] if len(results[0]) > 3 else {}
        if score < threshold:
            return None

        # Ambiguity Check: If multiple plausible matches exist with distinct policies/answers, escalate to RAG
        if len(results) > 1:
            score2, ans2_id, q2_id = results[1][:3]
            if (score - score2) < 0.02 and ans2_id != answer_id:
                return None

        ans = db.session.get(CompiledAnswer, answer_id)
        if not ans or ans.status != "validated":
            return None

        evidence_filter = get_evidence_filter()
        pol_id = meta.get("policy_id")
        ver_id = meta.get("version_id")
        p_name = meta.get("policy_name")
        v_num = meta.get("version_number")
        c_id = meta.get("chunk_id")
        section = meta.get("section", "General")
        page = meta.get("page", 1)
        question_text = meta.get("question")

        has_cached_meta = (
            pol_id is not None and ver_id is not None and p_name
            and p_name not in ("Policy", None, "N/A", "Unknown")
            and v_num and c_id
        )

        if has_cached_meta:
            # Pre-filter authorization check via cached allowed_policy_ids
            if scope and getattr(scope, "allowed_policy_ids", None) is not None:
                if pol_id not in scope.allowed_policy_ids:
                    return None

            t_date = getattr(scope, "target_date", None) if scope else None
            s_date = getattr(scope, "start_date", None) if scope else None
            e_date = getattr(scope, "end_date", None) if scope else None
            req_ver = getattr(scope, "requested_version", None) if scope else None
            needs_temporal_or_auth = bool(t_date or s_date or e_date or req_ver or (scope and getattr(scope, "allowed_policy_ids", None) is None))

            policy = None
            version = None
            if needs_temporal_or_auth:
                policy = db.session.get(Policy, pol_id)
                if not policy or (scope and not evidence_filter.is_authorized_for_policy(scope, policy)):
                    return None
                if req_ver or s_date or e_date or t_date:
                    version = db.session.get(PolicyVersion, ver_id)
                    if not version:
                        return None
                    if req_ver:
                        if str(version.version_num) != str(req_ver) and version.version_label != req_ver and f"v{version.version_num}" != req_ver:
                            return None
                    elif s_date or e_date:
                        if not version.is_valid_for_interval(s_date, e_date):
                            return None
                    elif t_date:
                        if not version.is_valid_for_date(t_date):
                            return None

            citations = [{
                "policy_id": pol_id,
                "version_id": ver_id,
                "policy_name": p_name,
                "version": str(v_num),
                "section": section,
                "page": page,
                "chunk_id": c_id
            }]

            ans_text = getattr(ans, "answer", None) or meta.get("answer_text", "")
            ans_conf = float(ans.confidence if ans.confidence is not None else score)

            return {
                "answer": ans_text,
                "score": float(score),
                "confidence": ans_conf,
                "matched_question": question_text or getattr(ans, "question_id", ""),
                "citations": citations,
                "policy": policy,
                "version": version,
                "source_chunk_ids": getattr(ans, "source_chunk_ids", None) or ([c_id] if c_id else []),
                "source_chunk": None
            }

        q_obj = db.session.get(CanonicalQuestion, ans.question_id) if ans.question_id else None
        if not q_obj:
            return None

        policy = db.session.get(Policy, q_obj.policy_id) if q_obj.policy_id else None
        version = db.session.get(PolicyVersion, q_obj.version_id) if q_obj.version_id else None

        if not policy or not version:
            return None

        # Verify source chunk existence in DB
        chunk = None
        if q_obj.source_chunk_id:
            chunk = PolicyChunkV2.query.filter_by(chunk_id=q_obj.source_chunk_id).first()
            if not chunk:
                # Source chunk was deleted or invalid -> reject compiled QA match
                return None

        if not chunk:
            chunk = PolicyChunkV2.query.filter_by(policy_id=policy.id, version_id=version.id).first()
            if not chunk:
                return None

        # Authoritative Authorization and Scope Validation
        if scope:
            if not evidence_filter.is_authorized_for_policy(scope, policy):
                return None

            t_date = getattr(scope, "target_date", None)
            s_date = getattr(scope, "start_date", None)
            e_date = getattr(scope, "end_date", None)
            req_ver = getattr(scope, "requested_version", None)

            if req_ver:
                if str(version.version_num) != str(req_ver) and version.version_label != req_ver and f"v{version.version_num}" != req_ver:
                    return None
            elif s_date or e_date:
                if not version.is_valid_for_interval(s_date, e_date):
                    return None
            elif t_date:
                if not version.is_valid_for_date(t_date):
                    return None
            elif getattr(scope, "current_only", True) and not getattr(scope, "historical", False):
                if not version.is_active and str(policy.status).lower() not in ("active", "published"):
                    return None

        section = chunk.section_path or "General"
        page = chunk.page or 1

        citations = [{
            "policy_id": policy.id,
            "version_id": version.id,
            "policy_name": policy.title,
            "version": version.version_number,
            "section": section,
            "page": page,
            "chunk_id": chunk.chunk_id
        }]

        return {
            "answer": ans.answer,
            "score": float(score),
            "confidence": float(ans.confidence if ans.confidence is not None else score),
            "matched_question": q_obj.question,
            "citations": citations,
            "policy": policy,
            "version": version,
            "source_chunk_ids": ans.source_chunk_ids,
            "source_chunk": chunk
        }
