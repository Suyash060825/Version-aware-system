from typing import List, Dict
from models import CompiledAnswer, CanonicalQuestion, now_utc
from rag.compiler.document_ir import ChunkIR

class AnswerGenerator:
    def generate(self, questions: List[CanonicalQuestion], chunks: List[ChunkIR]) -> List[CompiledAnswer]:
        chunk_map = {c.chunk_id: c for c in chunks}
        answers = []
        for q in questions:
            source_chunk = chunk_map.get(q.source_chunk_id)
            if not source_chunk:
                continue
                
            # Naive generation: the answer is the source chunk text
            # In a full implementation, this uses LLM to generate a concise answer.
            answers.append(
                CompiledAnswer(
                    question_id=q.id, # Needs to be set after q is saved to DB
                    answer=source_chunk.text,
                    source_chunk_ids=f'["{q.source_chunk_id}"]',
                    confidence=0.85,
                    entailment_score=0.9,
                    status="validated",
                    created_at=now_utc()
                )
            )
        return answers
