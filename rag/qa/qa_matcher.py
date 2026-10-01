"""
rag/qa/qa_matcher.py
Precomputed QA matcher returning validated answers with authoritative citations.
Strictly verifies that Policy, PolicyVersion, and Source Chunks exist in the database.
"""
from typing import List, Optional, Dict, Any
from models import db, CanonicalQuestion, CompiledAnswer, Policy, PolicyVersion, PolicyChunkV2
from rag.qa.qa_index import CanonicalQAIndex

class QAMatcher:
    def __init__(self):
        self.index = CanonicalQAIndex()

    def match(self, query: str, query_embedding: List[float], scope: Optional[Any] = None, threshold: float = 0.80) -> Optional[Dict[str, Any]]:
        results = self.index.search(query_embedding, top_k=8)
        if not results:
            return None

        from rag.authorization.evidence_filter import EvidenceFilter
        evidence_filter = EvidenceFilter()

        valid_candidates = []
        for score, answer_id, question_id in results:
            if score < threshold:
                continue

            ans = db.session.get(CompiledAnswer, answer_id)
            if not ans or ans.status != "validated":
                continue

            q_obj = db.session.get(CanonicalQuestion, ans.question_id) if ans.question_id else None
            if not q_obj:
                continue

            policy = db.session.get(Policy, q_obj.policy_id) if q_obj.policy_id else None
            version = db.session.get(PolicyVersion, q_obj.version_id) if q_obj.version_id else None
            if not policy or not version:
                continue

            # Verify source chunk existence in DB
            chunk = None
            if q_obj.source_chunk_id:
                chunk = PolicyChunkV2.query.filter_by(chunk_id=q_obj.source_chunk_id).first()
            if not chunk:
                chunk = PolicyChunkV2.query.filter_by(policy_id=policy.id, version_id=version.id).first()
            if not chunk:
                continue

            # Scope & Authorization validation
            if scope:
                if not evidence_filter.is_authorized_for_policy(scope, policy):
                    continue

                t_date = getattr(scope, "target_date", None)
                s_date = getattr(scope, "start_date", None)
                e_date = getattr(scope, "end_date", None)
                req_ver = getattr(scope, "requested_version", None)

                if req_ver:
                    if str(version.version_num) != str(req_ver) and version.version_label != req_ver and f"v{version.version_num}" != req_ver:
                        continue
                elif s_date or e_date:
                    if not version.is_valid_for_interval(s_date, e_date):
                        continue
                elif t_date:
                    if not version.is_valid_for_date(t_date):
                        continue
                elif getattr(scope, "current_only", True) and not getattr(scope, "historical", False):
                    # For current inquiries, prefer active versions when multiple exist
                    if not version.is_active and str(policy.status).lower() not in ("active", "published"):
                        continue

            valid_candidates.append({
                "score": float(score),
                "ans": ans,
                "q_obj": q_obj,
                "policy": policy,
                "version": version,
                "chunk": chunk
            })

        if not valid_candidates:
            return None

        # Sort valid candidates: highest score first, tie-break by active version
        valid_candidates.sort(key=lambda x: (x["score"], 1 if x["version"].is_active else 0), reverse=True)
        top = valid_candidates[0]

        # Ambiguity check: ONLY if another valid candidate is from a DIFFERENT policy with virtually identical score
        if len(valid_candidates) > 1:
            second = valid_candidates[1]
            if (top["score"] - second["score"]) < 0.02 and second["policy"].id != top["policy"].id:
                return None

        chunk = top["chunk"]
        policy = top["policy"]
        version = top["version"]
        ans = top["ans"]
        q_obj = top["q_obj"]
        score = top["score"]

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
