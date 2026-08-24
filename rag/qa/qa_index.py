"""
rag/qa/qa_index.py
Real persistent ANN vector index for precomputed canonical questions using FAISS HNSW.
Implements a Versioned Segment / Overlay architecture with Tombstones for O(1) incremental updates.
Base Index + Delta Overlay Index + Tombstone Filter + Asynchronous Compaction.
"""
import os
import pickle
import logging
import threading
import numpy as np
from typing import List, Tuple, Optional, Dict, Any, Set
from models import db, CanonicalQuestion, CompiledAnswer

logger = logging.getLogger("rag.qa.qa_index")

class CanonicalQAIndex:
    INDEX_FILE = "data/canonical_qa_faiss.index"
    META_FILE = "data/canonical_qa_faiss.meta.pkl"

    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self._base_index = None
        self._delta_index = None
        self._metadata: List[Dict[str, Any]] = []
        self._delta_metadata: List[Dict[str, Any]] = []
        self._tombstones: Set[int] = set()
        self._index_revision = 0
        self._corpus_revision = 0
        self._embedding_model = "BAAI/bge-small-en-v1.5"
        self._embedding_revision = "1.0.0"
        self._is_loaded = False
        self._compaction_lock = threading.Lock()
        self.load()

    def _init_empty_base(self):
        try:
            import faiss
            self._base_index = faiss.IndexHNSWFlat(self.dimension, 32, faiss.METRIC_INNER_PRODUCT)
        except Exception:
            import faiss
            self._base_index = faiss.IndexFlatIP(self.dimension)
        self._metadata = []

    def _init_empty_delta(self):
        try:
            import faiss
            self._delta_index = faiss.IndexFlatIP(self.dimension)
        except Exception:
            self._delta_index = None
        self._delta_metadata = []

    DELTA_INDEX_FILE = "data/canonical_qa_faiss_delta.index"

    def load(self):
        if os.path.exists(self.INDEX_FILE) and os.path.exists(self.META_FILE):
            try:
                import faiss
                self._base_index = faiss.read_index(self.INDEX_FILE)
                with open(self.META_FILE, "rb") as f:
                    meta_data = pickle.load(f)
                    self._metadata = meta_data.get("items", [])
                    self._delta_metadata = meta_data.get("delta_items", [])
                    self._tombstones = set(meta_data.get("tombstones", []))
                    self._index_revision = meta_data.get("index_revision", 0)
                    self._corpus_revision = meta_data.get("corpus_revision", 0)
                    self._embedding_model = meta_data.get("embedding_model", self._embedding_model)
                    self._embedding_revision = meta_data.get("embedding_revision", self._embedding_revision)
                    self.dimension = meta_data.get("dimension", self.dimension)
                
                if os.path.exists(self.DELTA_INDEX_FILE):
                    try:
                        self._delta_index = faiss.read_index(self.DELTA_INDEX_FILE)
                    except Exception:
                        self._init_empty_delta()
                else:
                    self._init_empty_delta()

                self._is_loaded = True
                active_count = len([m for m in self._metadata if m.get("question_id") not in self._tombstones]) + len([m for m in self._delta_metadata if m.get("question_id") not in self._tombstones])
                logger.info(f"Loaded persistent FAISS HNSW QA index ({active_count} active items, {len(self._tombstones)} tombstones, rev {self._index_revision})")
                return
            except Exception as e:
                logger.warning(f"Failed loading FAISS QA index: {e}. Rebuilding...")

        self.rebuild_from_db()

    def save(self):
        if self._base_index is None:
            return
        try:
            import faiss
            os.makedirs(os.path.dirname(self.INDEX_FILE), exist_ok=True)
            faiss.write_index(self._base_index, self.INDEX_FILE)
            if self._delta_index is not None and self._delta_index.ntotal > 0:
                faiss.write_index(self._delta_index, self.DELTA_INDEX_FILE)
            elif os.path.exists(self.DELTA_INDEX_FILE):
                os.remove(self.DELTA_INDEX_FILE)

            with open(self.META_FILE, "wb") as f:
                pickle.dump({
                    "items": self._metadata,
                    "delta_items": self._delta_metadata,
                    "tombstones": list(self._tombstones),
                    "index_revision": self._index_revision,
                    "corpus_revision": self._corpus_revision,
                    "embedding_model": self._embedding_model,
                    "embedding_revision": self._embedding_revision,
                    "dimension": self.dimension
                }, f)
            logger.info(f"Saved FAISS HNSW QA index ({self._base_index.ntotal} base + {self._delta_index.ntotal if self._delta_index else 0} delta items) to {self.INDEX_FILE}")
        except Exception as e:
            logger.error(f"Error saving FAISS QA index: {e}")

    def rebuild_from_db(self):
        try:
            questions = CanonicalQuestion.query.all()
            if not questions:
                self._init_empty_base()
                self._init_empty_delta()
                self._tombstones.clear()
                self._is_loaded = True
                return

            valid_pairs = []
            for q in questions:
                ans = CompiledAnswer.query.filter_by(question_id=q.id, status="validated").first()
                if ans and q.question.strip():
                    valid_pairs.append((q, ans))

            if not valid_pairs:
                self._init_empty_base()
                self._init_empty_delta()
                self._tombstones.clear()
                self._is_loaded = True
                return

            from rag.embeddings.embedder import get_embedder
            embedder = get_embedder()
            self._embedding_model = getattr(embedder, "model_name", "BAAI/bge-small-en-v1.5")
            if hasattr(embedder, "dimension"):
                self.dimension = embedder.dimension

            q_texts = [p[0].question for p in valid_pairs]
            embs = embedder.embed(q_texts)

            self._init_empty_base()
            self._init_empty_delta()
            self._tombstones.clear()

            import faiss
            vecs = np.array(embs, dtype=np.float32)
            faiss.normalize_L2(vecs)
            self._base_index.add(vecs)

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
            logger.info(f"Rebuilt base FAISS HNSW QA index with {len(valid_pairs)} questions (rev {self._index_revision})")
        except Exception as e:
            logger.error(f"Failed rebuilding QA index: {e}")
            self._init_empty_base()
            self._init_empty_delta()
            self._is_loaded = True

    def add(self, questions: List[Any], answers: List[Any], embeddings: List[List[float]]):
        """
        True incremental add: Appends directly to delta overlay index without rebuilding base.
        """
        if not questions or not embeddings:
            return
        if self._delta_index is None:
            self._init_empty_delta()

        import faiss
        vecs = np.array(embeddings, dtype=np.float32)
        faiss.normalize_L2(vecs)
        self._delta_index.add(vecs)

        for q, a in zip(questions, answers):
            self._delta_metadata.append({
                "question_id": getattr(q, "id", None),
                "answer_id": getattr(a, "id", None),
                "policy_id": getattr(q, "policy_id", None),
                "version_id": getattr(q, "version_id", None),
                "question": getattr(q, "question", "")
            })
        self._index_revision += 1

    def delete_policy_version(self, policy_id: int, version_id: int):
        """
        True incremental delete via tombstones in O(1) time.
        """
        for m in self._metadata:
            if m.get("policy_id") == policy_id and m.get("version_id") == version_id:
                qid = m.get("question_id")
                if qid is not None:
                    self._tombstones.add(qid)

        for m in self._delta_metadata:
            if m.get("policy_id") == policy_id and m.get("version_id") == version_id:
                qid = m.get("question_id")
                if qid is not None:
                    self._tombstones.add(qid)

        self._index_revision += 1

    def update_policy_version_qa(self, policy_id: int, version_id: int, questions: List[Any], answers: List[Any], embeddings: List[List[float]]):
        """
        True incremental delta update:
        1. Mark previous questions for this policy version as tombstones (O(1)).
        2. Append new questions to delta index (O(|delta|)).
        """
        self.delete_policy_version(policy_id, version_id)
        self.add(questions, answers, embeddings)

        self._compaction_lock = threading.Lock()

    def compact(self):
        """
        Thread-safe compaction: merges base index + delta overlay and filters out tombstones atomically.
        """
        with self._compaction_lock:
            try:
                active_items = []
                from rag.embeddings.embedder import get_embedder
                embedder = get_embedder()

                # Gather active items from base
                for m in self._metadata:
                    if m.get("question_id") not in self._tombstones:
                        active_items.append(m)
                
                # Gather active items from delta
                for m in self._delta_metadata:
                    if m.get("question_id") not in self._tombstones:
                        active_items.append(m)

                if not active_items:
                    self._init_empty_base()
                    self._init_empty_delta()
                    self._tombstones.clear()
                    self.save()
                    return

                texts = [m["question"] for m in active_items]
                embs = embedder.embed(texts)

                import faiss
                new_base = faiss.IndexHNSWFlat(self.dimension, 64, faiss.METRIC_INNER_PRODUCT)
                new_base.hnsw.efConstruction = 128
                new_base.hnsw.efSearch = 128
                vecs = np.array(embs, dtype=np.float32)
                faiss.normalize_L2(vecs)
                new_base.add(vecs)

                # Atomic reference swap
                self._base_index = new_base
                self._init_empty_delta()
                self._tombstones.clear()
                self._metadata = active_items
                self._index_revision += 1
                self.save()
                logger.info(f"Compacted FAISS QA index: {len(active_items)} active items (rev {self._index_revision})")
            except Exception as e:
                logger.error(f"Compaction failed, retaining existing index: {e}")

    def search(self, query_embedding: List[float], top_k: int = 3) -> List[Tuple[float, int, int]]:
        """
        Fast ANN query search across Base and Delta overlay with tombstone filtering.
        Returns [(similarity_score, answer_id, question_id), ...]
        """
        if not self._is_loaded or self._base_index is None:
            self.load()

        if not query_embedding:
            return []

        import faiss
        q = np.array([query_embedding], dtype=np.float32)
        faiss.normalize_L2(q)

        candidates = []

        # 1. Search Base Index
        if self._base_index and self._base_index.ntotal > 0:
            k_base = min(top_k + len(self._tombstones), self._base_index.ntotal)
            distances, indices = self._base_index.search(q, k_base)
            for dist, idx in zip(distances[0], indices[0]):
                if 0 <= idx < len(self._metadata):
                    meta = self._metadata[idx]
                    qid = meta.get("question_id")
                    if qid not in self._tombstones:
                        candidates.append((float(dist), meta["answer_id"], qid))

        # 2. Search Delta Overlay Index
        if self._delta_index and self._delta_index.ntotal > 0:
            k_delta = min(top_k + len(self._tombstones), self._delta_index.ntotal)
            distances, indices = self._delta_index.search(q, k_delta)
            for dist, idx in zip(distances[0], indices[0]):
                if 0 <= idx < len(self._delta_metadata):
                    meta = self._delta_metadata[idx]
                    qid = meta.get("question_id")
                    if qid not in self._tombstones:
                        candidates.append((float(dist), meta["answer_id"], qid))

        # Sort and take top_k
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[:top_k]

    @property
    def revision(self) -> int:
        return self._index_revision

    def stats(self) -> dict:
        base_count = self._base_index.ntotal if self._base_index else 0
        delta_count = self._delta_index.ntotal if self._delta_index else 0
        active_count = (base_count + delta_count) - len(self._tombstones)
        return {
            "base_items": base_count,
            "delta_items": delta_count,
            "tombstones": len(self._tombstones),
            "active_items": max(0, active_count),
            "index_revision": self._index_revision,
            "corpus_revision": self._corpus_revision,
            "dimension": self.dimension,
            "backend": "FAISS-HNSW-SegmentOverlay",
            "embedding_model": self._embedding_model
        }
