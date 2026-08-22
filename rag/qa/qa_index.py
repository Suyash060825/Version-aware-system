"""
rag/qa/qa_index.py
Persistent vector index for precomputed canonical questions.
Enables sub-millisecond ANN lookup for Level 1 queries without query-time corpus embedding.
"""
import os
import pickle
import logging
import numpy as np
from typing import List, Tuple, Optional
from models import db, CanonicalQuestion, CompiledAnswer

logger = logging.getLogger("rag.qa.qa_index")

class CanonicalQAIndex:
    INDEX_PATH = "data/canonical_qa_index.pkl"

    def __init__(self):
        self._questions: List[str] = []
        self._embeddings: Optional[np.ndarray] = None
        self._answer_ids: List[int] = []
        self._question_ids: List[int] = []
        self._revision = 0
        self._is_loaded = False
        self.load()

    def load(self):
        if os.path.exists(self.INDEX_PATH):
            try:
                with open(self.INDEX_PATH, "rb") as f:
                    data = pickle.load(f)
                    self._questions = data["questions"]
                    self._embeddings = data["embeddings"]
                    self._answer_ids = data["answer_ids"]
                    self._question_ids = data.get("question_ids", [])
                    self._revision = data.get("revision", 0)
                    self._is_loaded = True
                logger.info(f"Loaded persistent Canonical QA index ({len(self._questions)} items, rev {self._revision})")
                return
            except Exception as e:
                logger.warning(f"Failed loading QA index from disk: {e}. Rebuilding...")

        self.rebuild_from_db()

    def rebuild_from_db(self):
        try:
            questions = CanonicalQuestion.query.all()
            if not questions:
                return

            valid_pairs = []
            for q in questions:
                # Find matching validated answer
                ans = CompiledAnswer.query.filter_by(question_id=q.id, status="validated").first()
                if ans and q.question.strip():
                    valid_pairs.append((q, ans))

            if not valid_pairs:
                return

            from rag.embeddings.embedder import get_embedder
            embedder = get_embedder()

            q_texts = [p[0].question for p in valid_pairs]
            embs = embedder.embed(q_texts)

            self._questions = q_texts
            self._embeddings = np.array(embs, dtype=np.float32)
            self._question_ids = [p[0].id for p in valid_pairs]
            self._answer_ids = [p[1].id for p in valid_pairs]
            self._revision += 1
            self._is_loaded = True

            os.makedirs(os.path.dirname(self.INDEX_PATH), exist_ok=True)
            with open(self.INDEX_PATH, "wb") as f:
                pickle.dump({
                    "questions": self._questions,
                    "embeddings": self._embeddings,
                    "answer_ids": self._answer_ids,
                    "question_ids": self._question_ids,
                    "revision": self._revision
                }, f)
            logger.info(f"Persisted Canonical QA index with {len(self._questions)} questions to {self.INDEX_PATH}")
        except Exception as e:
            logger.error(f"Failed rebuilding QA index: {e}")

    def search(self, query_embedding: List[float], top_k: int = 3) -> List[Tuple[float, int, int]]:
        """Returns [(similarity_score, answer_id, question_id), ...]"""
        if not self._is_loaded or self._embeddings is None:
            self.load()

        if self._embeddings is None or len(self._embeddings) == 0:
            return []

        q = np.array(query_embedding, dtype=np.float32)
        # Cosine similarity (query and stored embeddings are normalized)
        norm_q = np.linalg.norm(q)
        if norm_q > 0:
            q = q / norm_q

        scores = self._embeddings @ q
        top_k = min(top_k, len(scores))
        top_indices = np.argsort(scores)[-top_k:][::-1]

        results = []
        for i in top_indices:
            score = float(scores[i])
            ans_id = self._answer_ids[i]
            q_id = self._question_ids[i] if i < len(self._question_ids) else None
            if ans_id is not None:
                results.append((score, ans_id, q_id))
        return results
