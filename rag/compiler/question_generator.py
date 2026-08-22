import os
import json
from typing import List
from models import CanonicalQuestion, now_utc
from rag.compiler.document_ir import ChunkIR
import hashlib

class QuestionGenerator:
    """
    Generates canonical questions for policy chunks.
    """
    def __init__(self):
        self.enabled = os.environ.get("COMPILER_QA_ENABLED", "true").lower() == "true"
        self.max_questions = int(os.environ.get("COMPILER_MAX_QUESTIONS_PER_CHUNK", "3"))

    def generate(self, chunks: List[ChunkIR]) -> List[CanonicalQuestion]:
        if not self.enabled:
            return []
            
        questions = []
        for chunk in chunks:
            # Naive mock generation based on chunk content. 
            # In a full implementation, this calls the LLM with QUESTION_GENERATION_PROMPT.
            if "leave" in chunk.text.lower():
                q_text = "What is the policy regarding leave?"
                q_hash = hashlib.sha256(q_text.encode()).hexdigest()
                questions.append(
                    CanonicalQuestion(
                        policy_id=chunk.policy_id,
                        version_id=chunk.version_id,
                        source_chunk_id=chunk.chunk_id,
                        question=q_text,
                        question_hash=q_hash,
                        quality_score=0.9,
                        created_at=now_utc()
                    )
                )
        return questions
