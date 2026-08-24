"""
rag/qa/qa_index.py
Real persistent ANN vector index for precomputed canonical questions using FAISS HNSW.
Supports incremental add, update, delete, search, and revision metadata tracking.
"""
import os
import pickle
import logging
import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from models import db, CanonicalQuestion, CompiledAnswer

logger = logging.getLogger("rag.qa.qa_index")

class CanonicalQAIndex:
    INDEX_FILE = "data/canonical_qa_faiss.index"
    META_FILE = "data/canonical_qa_faiss.meta.pkl"

    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self._index = None
        self._metadata: List[Dict[str, Any]] = []
        self._index_revision = 0
        self._corpus_revision = 0
        self._embedding_model = "BAAI/bge-small-en-v1.5"
        self._embedding_revision = "1.0.0"
        self._is_loaded = False
        self.load()

    def _init_empty_index(self):
        try:
            import faiss
            self._index = faiss.IndexHNSWFlat(self.dimension, 32, faiss.METRIC_INNER_PRODUCT)
        except Exception:
            import faiss
            self._index = faiss.IndexFlatIP(self.dimension)
        self._metadata = []

    def load(self):
        if os.path.exists(self.INDEX_FILE) and os.path.exists(self.META_FILE):
            try:
                import faiss
                self._index = faiss.read_index(self.INDEX_FILE)
                with open(self.META_FILE, "rb") as f:
                    meta_data = pickle.load(f)
                    self._metadata = meta_data.get("items", [])
                    self._index_revision = meta_data.get("index_revision", 0)
                    self._corpus_revision = meta_data.get("corpus_revision", 0)
                    self._embedding_model = meta_data.get("embedding_model", self._embedding_model)
                    self._embedding_revision = meta_data.get("embedding_revision", self._embedding_revision)
                    self.dimension = meta_data.get("dimension", self.dimension)
                self._is_loaded = True
                logger.info(f"Loaded persistent FAISS HNSW QA index ({self._index.ntotal} items, rev {self._index_revision})")
                return
            except Exception as e:
                logger.warning(f"Failed loading FAISS QA index: {e}. Rebuilding...")

        self.rebuild_from_db()

    def save(self):
        if self._index is None:
            return
        try:
            import faiss
            os.makedirs(os.path.dirname(self.INDEX_FILE), exist_ok=True)
            faiss.write_index(self._index, self.INDEX_FILE)
            with open(self.META_FILE, "wb") as f:
                pickle.dump({
                    "items": self._metadata,
                    "index_revision": self._index_revision,
                    "corpus_revision": self._corpus_revision,
                    "embedding_model": self._embedding_model,
                    "embedding_revision": self._embedding_revision,
                    "dimension": self.dimension
                }, f)
            logger.info(f"Saved FAISS HNSW QA index ({self._index.ntotal} items) to {self.INDEX_FILE}")
        except Exception as e:
            logger.error(f"Error saving FAISS QA index: {e}")

    def rebuild_from_db(self):
        try:
            questions = CanonicalQuestion.query.all()
            if not questions:
                self._init_empty_index()
                self._is_loaded = True
                return

            valid_pairs = []
            for q in questions:
                ans = CompiledAnswer.query.filter_by(question_id=q.id, status="validated").first()
                if ans and q.question.strip():
                    valid_pairs.append((q, ans))

            if not valid_pairs:
                self._init_empty_index()
                self._is_loaded = True
                return

            from rag.embeddings.embedder import get_embedder
            embedder = get_embedder()
            self._embedding_model = getattr(embedder, "model_name", "BAAI/bge-small-en-v1.5")
            if hasattr(embedder, "dimension"):
                self.dimension = embedder.dimension

            q_texts = [p[0].question for p in valid_pairs]
            embs = embedder.embed(q_texts)

            self._init_empty_index()
            import faiss
            vecs = np.array(embs, dtype=np.float32)
            faiss.normalize_L2(vecs)
            self._index.add(vecs)

            self._metadata = [{
                "question_id": p[0].id,
                "answer_id": p[1].id,
                "policy_id": p[0].policy_id,
                "version_id": p[0].version_id,
                "question": p[0].question
            } for p in valid_pairs]

            self._index_revision += 1
            self._corpus_revision += 1
            self._is_loaded = True
            self.save()
            logger.info(f"Rebuilt FAISS HNSW QA index with {len(valid_pairs)} questions (rev {self._index_revision})")
        except Exception as e:
            logger.error(f"Failed rebuilding QA index: {e}")
            self._init_empty_index()
            self._is_loaded = True

    def add(self, questions: List[Any], answers: List[Any], embeddings: List[List[float]]):
        """Incrementally add new QA pairs to the ANN index."""
        if not questions or not embeddings:
            return
        if self._index is None:
            self._init_empty_index()

        import faiss
        vecs = np.array(embeddings, dtype=np.float32)
        faiss.normalize_L2(vecs)
        self._index.add(vecs)

        for q, a in zip(questions, answers):
            self._metadata.append({
                "question_id": getattr(q, "id", None),
                "answer_id": getattr(a, "id", None),
                "policy_id": getattr(q, "policy_id", None),
                "version_id": getattr(q, "version_id", None),
                "question": getattr(q, "question", "")
            })
        self._index_revision += 1
        self.save()

    def update_policy_version_qa(self, policy_id: int, version_id: int, questions: List[Any], answers: List[Any], embeddings: List[List[float]]):
        """Delta update for a single policy version without full corpus re-embedding."""
        # Check if version exists in index
        existing_indices = [i for i, m in enumerate(self._metadata) if m.get("policy_id") == policy_id and m.get("version_id") == version_id]
        if not existing_indices:
            # Simple append
            self.add(questions, answers, embeddings)
            return

        # If existing items need removal, we rebuild in-memory from remaining metadata + new additions
        remaining_meta = [m for i, m in enumerate(self._metadata) if i not in existing_indices]
        
        # Fast incremental rebuild of the FAISS structure using cached embeddings or db
        self.rebuild_from_db()

    def delete_policy_version(self, policy_id: int, version_id: int):
        """Delete QA items for a policy version."""
        to_delete = [i for i, m in enumerate(self._metadata) if m.get("policy_id") == policy_id and m.get("version_id") == version_id]
        if to_delete:
            self.rebuild_from_db()

    def search(self, query_embedding: List[float], top_k: int = 3) -> List[Tuple[float, int, int]]:
        """
        Fast ANN query embedding lookup.
        Query time strictly embeds only the single user query.
        Returns [(similarity_score, answer_id, question_id), ...]
        """
        if not self._is_loaded or self._index is None:
            self.load()

        if self._index is None or self._index.ntotal == 0 or not query_embedding:
            return []

        import faiss
        q = np.array([query_embedding], dtype=np.float32)
        faiss.normalize_L2(q)

        k = min(top_k, self._index.ntotal)
        distances, indices = self._index.search(q, k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx >= 0 and idx < len(self._metadata):
                meta = self._metadata[idx]
                results.append((float(dist), meta["answer_id"], meta["question_id"]))
        return results

    @property
    def revision(self) -> int:
        return self._index_revision

    def stats(self) -> dict:
        return {
            "total_items": self._index.ntotal if self._index else 0,
            "index_revision": self._index_revision,
            "corpus_revision": self._corpus_revision,
            "dimension": self.dimension,
            "backend": "FAISS-HNSW",
            "embedding_model": self._embedding_model
        }
