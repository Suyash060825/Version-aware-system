from typing import List, Optional
from rag.qa.qa_index import CanonicalQAIndex
from rag.qa.answer_store import AnswerStore

class QAMatcher:
    def __init__(self):
        self.index = CanonicalQAIndex()
        self.store = AnswerStore()
        
    def match(self, query: str, query_embedding: List[float], threshold: float = 0.85) -> Optional[dict]:
        results = self.index.search(query_embedding, top_k=1)
        if not results:
            return None
            
        score, answer_id = results[0]
        if score >= threshold:
            ans = self.store.get_answer(answer_id)
            if ans and ans.status == "validated":
                return {
                    "answer": ans.answer,
                    "score": score,
                    "confidence": ans.confidence,
                    "source_chunk_ids": ans.source_chunk_ids
                }
        return None
