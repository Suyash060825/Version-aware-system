import os
import json
import logging
import hashlib
import time
import math
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)

class MultiLevelCache:
    """
    Multi-tier Caching Engine:
    L1: Exact normalized query hash cache (In-Memory + Redis, TTL=1h)
    L2: Semantic vector cache (Cosine similarity >= 0.95, In-Memory + Redis)
    """
    def __init__(self):
        self.use_redis = False
        self.redis = None
        redis_url = os.environ.get("REDIS_URL")
        if redis_url:
            try:
                import redis
                self.redis = redis.Redis.from_url(redis_url)
                self.redis.ping()
                self.use_redis = True
                logger.info("MultiLevelCache connected to Redis.")
            except Exception as e:
                logger.warning(f"Redis not available: {e}. Falling back to in-memory.")

        self._local_l1: Dict[str, dict] = {}
        self._local_l2: List[dict] = []
        self._max_local = 2000

    def _hash_query(self, query: str, scope_key: str = "") -> str:
        clean = f"{query.strip().lower()}|{scope_key}"
        return hashlib.sha256(clean.encode()).hexdigest()

    def get_l1(self, query_hash: str, scope_key: str = "") -> Optional[dict]:
        key = f"l1:{scope_key}:{query_hash}"
        if self.use_redis:
            try:
                data = self.redis.get(key)
                if data:
                    return json.loads(data)
            except Exception:
                pass
        item = self._local_l1.get(key)
        if item:
            if time.time() < item.get("expires_at", 0):
                return item.get("data")
            else:
                self._local_l1.pop(key, None)
        return None

    def set_l1(self, query_hash: str, scope_key: str, result: dict, ttl: int = 3600):
        key = f"l1:{scope_key}:{query_hash}"
        if self.use_redis:
            try:
                self.redis.setex(key, ttl, json.dumps(result))
            except Exception:
                pass
        if len(self._local_l1) > self._max_local:
            self._local_l1.clear()
        self._local_l1[key] = {
            "data": result,
            "expires_at": time.time() + ttl
        }

    def get_l2(self, query_embedding: List[float], scope_key: str = "", threshold: float = 0.95) -> Optional[dict]:
        if not query_embedding:
            return None
        now = time.time()
        for item in reversed(self._local_l2):
            if item.get("expires_at", 0) < now:
                continue
            if item.get("scope_key") == scope_key:
                cached_vec = item.get("embedding")
                if cached_vec:
                    sim = _cosine_similarity(query_embedding, cached_vec)
                    if sim >= threshold:
                        return item.get("data")
        return None

    def set_l2(self, query_embedding: List[float], scope_key: str, result: dict, policy_ids: Optional[List[int]] = None, ttl: int = 3600):
        if not query_embedding:
            return
        if len(self._local_l2) > self._max_local:
            self._local_l2 = self._local_l2[-500:]
        self._local_l2.append({
            "embedding": query_embedding,
            "scope_key": scope_key,
            "data": result,
            "policy_ids": policy_ids or [],
            "expires_at": time.time() + ttl
        })

    def get(self, query_embedding: List[float], allowed_depts: Optional[List[str]] = None, is_diff_query: bool = False) -> Optional[dict]:
        scope = ",".join(sorted(allowed_depts or [])) + f"|diff={is_diff_query}"
        return self.get_l2(query_embedding, scope_key=scope)

    def put(self, query_embedding: List[float], answer: str, citations: list, chunks_used: int, allowed_depts: Optional[List[str]] = None, model: str = "", is_diff_query: bool = False):
        scope = ",".join(sorted(allowed_depts or [])) + f"|diff={is_diff_query}"
        policy_ids = [c.get("policy_id") for c in citations if c.get("policy_id")]
        res = {
            "answer": answer,
            "citations": citations,
            "chunks_used": chunks_used,
            "model": model,
            "confidence": 100
        }
        self.set_l2(query_embedding, scope_key=scope, result=res, policy_ids=policy_ids)

    def invalidate_policy(self, policy_id: int):
        """Purge all cached results touching a modified policy."""
        self._local_l1.clear()
        self._local_l2 = [
            item for item in self._local_l2
            if policy_id not in item.get("policy_ids", [])
        ]
        if self.use_redis:
            try:
                # Scan and delete l1 keys
                for key in self.redis.scan_iter("l1:*"):
                    self.redis.delete(key)
            except Exception:
                pass
        logger.info(f"Invalidated cache for policy {policy_id}")

    def invalidate_version(self, policy_id: int, version_id: int):
        self.invalidate_policy(policy_id)

_CACHE = None
def get_cache() -> MultiLevelCache:
    global _CACHE
    if _CACHE is None:
        _CACHE = MultiLevelCache()
    return _CACHE
