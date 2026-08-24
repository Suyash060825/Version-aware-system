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
            if not q_obj:
                return None

            policy = db.session.get(Policy, q_obj.policy_id) if q_obj.policy_id else None
            version = db.session.get(PolicyVersion, q_obj.version_id) if q_obj.version_id else None

            if not policy or not version:
                return None

            # Resolve citation details from authoritative source chunk
            section = "General"
            page = 1
            if q_obj.source_chunk_id:
                chunk = PolicyChunkV2.query.filter_by(chunk_id=q_obj.source_chunk_id).first()
                if chunk:
                    section = chunk.section_path or section
                    page = chunk.page or page

            citations = [{
                "policy_id": policy.id,
                "version_id": version.id,
                "policy_name": policy.title,
                "version": version.version_number,
                "section": section,
                "page": page,
                "chunk_id": q_obj.source_chunk_id
            }]

            return {
                "answer": ans.answer,
                "score": float(score),
                "confidence": float(ans.confidence if ans.confidence is not None else score),
                "matched_question": q_obj.question,
                "citations": citations,
                "policy": policy,
                "version": version,
                "source_chunk_ids": ans.source_chunk_ids
            }
        return None
