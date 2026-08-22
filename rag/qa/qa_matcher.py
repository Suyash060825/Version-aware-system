"""
rag/qa/qa_matcher.py
Precomputed QA matcher returning validated answers with authoritative citations.
"""
from typing import List, Optional, Dict, Any
from models import db, CanonicalQuestion, CompiledAnswer, Policy, PolicyVersion, PolicyChunkV2
from rag.qa.qa_index import CanonicalQAIndex

class QAMatcher:
    def __init__(self):
        self.index = CanonicalQAIndex()

    def match(self, query: str, query_embedding: List[float], threshold: float = 0.80) -> Optional[Dict[str, Any]]:
        results = self.index.search(query_embedding, top_k=1)
        if not results:
            return None

        score, answer_id, question_id = results[0]
        if score >= threshold:
            ans = db.session.get(CompiledAnswer, answer_id)
            if not ans or ans.status != "validated":
                return None

            q_obj = db.session.get(CanonicalQuestion, ans.question_id) if ans.question_id else None
            policy = db.session.get(Policy, q_obj.policy_id) if q_obj else None
            version = db.session.get(PolicyVersion, q_obj.version_id) if q_obj else None

            # Resolve citation details
            section = "General"
            page = 1
            if q_obj and q_obj.source_chunk_id:
                chunk = PolicyChunkV2.query.filter_by(chunk_id=q_obj.source_chunk_id).first()
                if chunk:
                    section = chunk.section_path or section
                    page = chunk.page or page

            citations = [{
                "policy_id": policy.id if policy else 1,
                "version_id": version.id if version else 1,
                "policy_name": policy.title if policy else "Policy",
                "version": version.version_number if version else "1.0",
                "section": section,
                "page": page,
                "chunk_id": q_obj.source_chunk_id if q_obj else None
            }]

            return {
                "answer": ans.answer,
                "score": float(score),
                "confidence": float(ans.confidence or score),
                "matched_question": q_obj.question if q_obj else "",
                "citations": citations,
                "source_chunk_ids": ans.source_chunk_ids
            }
        return None
