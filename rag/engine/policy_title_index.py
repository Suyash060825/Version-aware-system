"""
rag/engine/policy_title_index.py
Lightweight semantic policy title index for accurate policy identification and anchoring.
Eliminates wrong policy selection caused by substring collisions across large policy corpora.
"""
import logging
from typing import Optional, List, Tuple, Set
import numpy as np

logger = logging.getLogger(__name__)


class PolicyTitleIndex:
    def __init__(self):
        self.policy_ids: List[int] = []
        self.titles: List[str] = []
        self.embeddings: Optional[np.ndarray] = None  # shape: (N, D), unit normalized
        self._is_building: bool = False

    def build_or_rebuild(self) -> None:
        """
        Embeds all distinct policy titles in the database and caches as a normalized numpy matrix.
        """
        if self._is_building:
            return
        self._is_building = True
        try:
            from models import Policy, db
            from rag.embeddings.embedder import get_embedder

            policies = Policy.query.all()
            if not policies:
                self.policy_ids = []
                self.titles = []
                self.embeddings = None
                return

            valid = [(p.id, p.title.strip()) for p in policies if p.title and p.title.strip()]
            if not valid:
                self.policy_ids = []
                self.titles = []
                self.embeddings = None
                return

            self.policy_ids = [v[0] for v in valid]
            self.titles = [v[1] for v in valid]

            embedder = get_embedder()
            raw_embs = embedder.embed(self.titles)
            arr = np.array(raw_embs, dtype=np.float32)
            norms = np.linalg.norm(arr, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            self.embeddings = arr / norms
            logger.info("PolicyTitleIndex built successfully with %d policies", len(self.policy_ids))
        except Exception as e:
            logger.warning("PolicyTitleIndex build_or_rebuild error: %s", e)
        finally:
            self._is_building = False

    def find_top_policy_similarity(self, q_emb: List[float]) -> Tuple[Optional[int], float]:
        """
        Computes cosine similarity between query embedding and cached title embeddings.
        Returns (top_policy_id, max_similarity).
        """
        if self.embeddings is None or len(self.policy_ids) == 0:
            self.build_or_rebuild()
        if self.embeddings is None or len(self.policy_ids) == 0:
            return None, 0.0

        q = np.array(q_emb, dtype=np.float32)
        norm = np.linalg.norm(q)
        if norm > 0:
            q = q / norm
        else:
            return None, 0.0

        sims = np.dot(self.embeddings, q)
        top_idx = int(np.argmax(sims))
        return self.policy_ids[top_idx], float(sims[top_idx])


_TITLE_INDEX: Optional[PolicyTitleIndex] = None


def get_policy_title_index() -> PolicyTitleIndex:
    global _TITLE_INDEX
    if _TITLE_INDEX is None:
        _TITLE_INDEX = PolicyTitleIndex()
    return _TITLE_INDEX


def rebuild_title_index() -> None:
    idx = get_policy_title_index()
    idx.build_or_rebuild()
