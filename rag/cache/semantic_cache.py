import os
import json
import logging
import hashlib
import time
import math
from collections import defaultdict
from typing import List, Dict, Optional, Any
from config import Config

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
        redis_url = Config.REDIS_URL
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
        self._local_l2: Dict[str, list] = defaultdict(list)
        self._max_local = 2000
        self._global_l2_max = 5000

    def _hash_query(self, query: str, scope_key: str = "") -> str:
        clean = f"{query.strip().lower()}|{scope_key}"
        return hashlib.sha256(clean.encode()).hexdigest()

    def get_l1(self, query_hash: str, scope_key: str = "") -> Optional[dict]:
        key = f"l1:{scope_key}:{query_hash}"
        if self.use_redis:
            try:
                data = self.redis.get(key)
                if data:
                    parsed = json.loads(data)
                    if isinstance(parsed, dict) and "data" in parsed:
                        return parsed["data"]
                    return parsed
            except Exception:
                pass
        item = self._local_l1.get(key)
        if item:
            if time.time() < item.get("expires_at", 0):
                return item.get("data")
            else:
                self._local_l1.pop(key, None)
        return None

    def set_l1(
        self,
        query_hash: str,
        scope_key: str,
        result: dict,
        policy_ids: Optional[List[int]] = None,
        version_ids: Optional[List[int]] = None,
        chunk_ids: Optional[List[str]] = None,
        ttl: int = 3600
    ):
        key = f"l1:{scope_key}:{query_hash}"
        item_data = {
            "data": result,
            "policy_ids": policy_ids or [],
            "version_ids": version_ids or [],
            "chunk_ids": chunk_ids or [],
            "expires_at": time.time() + ttl
        }
        if self.use_redis:
            try:
                self.redis.setex(key, ttl, json.dumps(item_data))
            except Exception as e:
                logger.warning(f"Redis setex failed in cache put_l1: {e}")
        if len(self._local_l1) > self._max_local:
            # Evict oldest 20% by expiry time (LRU approximation)
            sorted_keys = sorted(
                self._local_l1.keys(),
                key=lambda k: self._local_l1[k].get("expires_at", 0)
            )
            for k in sorted_keys[:self._max_local // 5]:
                self._local_l1.pop(k, None)
        self._local_l1[key] = item_data

    def get_l2(self, query_embedding: List[float], scope_key: str = "", threshold: float = 0.95) -> Optional[dict]:
        bucket = self._local_l2.get(scope_key)
        if not query_embedding or not bucket:
            return None
        now = time.time()
        # Filter candidate items by non-expiration in reverse order
        candidates = [
            item for item in reversed(bucket)
            if item.get("expires_at", 0) >= now and item.get("embedding")
        ]
        if not candidates:
            return None

        try:
            import numpy as np
            embeddings = np.array([item["embedding"] for item in candidates], dtype=np.float32)
            q_vec = np.array(query_embedding, dtype=np.float32)
            q_norm = np.linalg.norm(q_vec)
            if q_norm == 0:
                return None
            q_unit = q_vec / q_norm

            emb_norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            emb_norms[emb_norms == 0] = 1e-9
            normalized_embs = embeddings / emb_norms

            sims = np.dot(normalized_embs, q_unit)
            best_idx = int(np.argmax(sims))
            if sims[best_idx] >= threshold:
                return candidates[best_idx].get("data")
        except Exception as e:
            logger.warning(f"Vectorized L2 cosine scan fallback: {e}")
            for item in candidates:
                cached_vec = item.get("embedding")
                if cached_vec and _cosine_similarity(query_embedding, cached_vec) >= threshold:
                    return item.get("data")
        return None

    def set_l2(
        self,
        query_embedding: List[float],
        scope_key: str,
        result: dict,
        policy_ids: Optional[List[int]] = None,
        version_ids: Optional[List[int]] = None,
        chunk_ids: Optional[List[str]] = None,
        ttl: int = 3600
    ):
        if not query_embedding:
            return

        # Enforce global capacity cap across all scope buckets
        total_l2 = sum(len(v) for v in self._local_l2.values())
        if total_l2 >= self._global_l2_max:
            now = time.time()
            for sk in list(self._local_l2.keys()):
                self._local_l2[sk] = [item for item in self._local_l2[sk] if item.get("expires_at", 0) >= now]
                if not self._local_l2[sk]:
                    del self._local_l2[sk]
            total_l2 = sum(len(v) for v in self._local_l2.values())
            if total_l2 >= self._global_l2_max:
                for sk, bucket in sorted(self._local_l2.items(), key=lambda x: len(x[1]), reverse=True):
                    if len(bucket) > 50:
                        drop_count = max(1, int(len(bucket) * 0.3))
                        self._local_l2[sk] = bucket[drop_count:]
                    if sum(len(v) for v in self._local_l2.values()) < self._global_l2_max:
                        break

        if len(self._local_l2[scope_key]) > self._max_local:
            now = time.time()
            self._local_l2[scope_key] = [item for item in self._local_l2[scope_key] if item.get("expires_at", 0) >= now][-500:]
        self._local_l2[scope_key].append({
            "embedding": query_embedding,
            "scope_key": scope_key,
            "data": result,
            "policy_ids": policy_ids or [],
            "version_ids": version_ids or [],
            "chunk_ids": chunk_ids or [],
            "expires_at": time.time() + ttl
        })

    def _make_scope_key(self, scope: Optional[Any] = None, allowed_depts: Optional[List[str]] = None, is_diff_query: bool = False) -> str:
        if scope is not None and hasattr(scope, "role"):
            tenant = getattr(scope, "tenant_id", "") or ""
            role = getattr(scope, "role", "employee")
            depts = ",".join(sorted(getattr(scope, "departments", ()) or []))
            conf = ",".join(sorted(getattr(scope, "allowed_confidentiality", ()) or []))
            hist = getattr(scope, "historical", False)
            t_date = getattr(scope, "target_date", "") or ""
            ver = getattr(scope, "requested_version", "") or ""
            allowed_pids = getattr(scope, "allowed_policy_ids", None)
            if allowed_pids is not None:
                pids_hash = hashlib.md5(str(sorted(allowed_pids)).encode()).hexdigest()[:8]
            else:
                pids_hash = "all"
            return f"t={tenant}|r={role}|d={depts}|c={conf}|h={hist}|td={t_date}|v={ver}|pids={pids_hash}|diff={is_diff_query}"
        scope_str = ",".join(sorted(allowed_depts or [])) + f"|diff={is_diff_query}"
        return scope_str

    def get(self, query_embedding: Optional[List[float]] = None, query: Optional[str] = None, scope: Optional[Any] = None, allowed_depts: Optional[List[str]] = None, is_diff_query: bool = False) -> Optional[dict]:
        """
        Fast multi-tier cache lookup:
        - L1 exact hash cache check (sub-millisecond dict lookup) when query string provided.
        - L2 semantic vector cache scan when query_embedding provided.
        Chunk/version validity is trusted for its TTL window and invalidated on writes.
        Policy-level authorization is validated fail-closed.
        """
        scope_key = self._make_scope_key(scope=scope, allowed_depts=allowed_depts, is_diff_query=is_diff_query)
        
        cached = None
        # 1. Try L1 exact match first
        if query:
            q_hash = self._hash_query(query, scope_key)
            cached = self.get_l1(q_hash, scope_key=scope_key)
            
        # 2. Fall back to L2 semantic vector similarity
        if not cached and query_embedding:
            cached = self.get_l2(query_embedding, scope_key=scope_key)

        if not cached:
            return None

        # scope_key already enforces user role, departments, confidentiality, and policy authorization
        return cached

    def put(self, query_embedding: Optional[List[float]], answer: str, citations: list, chunks_used: int, scope: Optional[Any] = None, allowed_depts: Optional[List[str]] = None, model: str = "", confidence: Optional[float] = None, is_diff_query: bool = False, query: Optional[str] = None):
        scope_key = self._make_scope_key(scope=scope, allowed_depts=allowed_depts, is_diff_query=is_diff_query)
        policy_ids = [c.get("policy_id") for c in citations if c.get("policy_id")]
        version_ids = [c.get("version_id") for c in citations if c.get("version_id")]
        chunk_ids = [c.get("chunk_id") for c in citations if c.get("chunk_id")]
        
        # Preserve actual confidence score without inflating or hardcoding
        conf_val = float(confidence) if confidence is not None else 1.0

        res = {
            "answer": answer,
            "citations": citations,
            "chunks_used": chunks_used,
            "model": model,
            "confidence": conf_val
        }
        if query:
            q_hash = self._hash_query(query, scope_key)
            self.set_l1(
                q_hash,
                scope_key=scope_key,
                result=res,
                policy_ids=policy_ids,
                version_ids=version_ids,
                chunk_ids=chunk_ids
            )
        if query_embedding:
            self.set_l2(
                query_embedding,
                scope_key=scope_key,
                result=res,
                policy_ids=policy_ids,
                version_ids=version_ids,
                chunk_ids=chunk_ids
            )

    def invalidate_policy(self, policy_id: int):
        """Purge only cached entries touching a modified policy without clearing unrelated data."""
        keys_to_remove = []
        for key, item in list(self._local_l1.items()):
            if policy_id in item.get("policy_ids", []):
                keys_to_remove.append(key)
        for key in keys_to_remove:
            self._local_l1.pop(key, None)

        for sk in list(self._local_l2.keys()):
            self._local_l2[sk] = [
                item for item in self._local_l2[sk]
                if policy_id not in item.get("policy_ids", [])
            ]
        logger.info(f"Targeted invalidation for policy {policy_id}: removed {len(keys_to_remove)} L1 entries")

    def invalidate_version(self, policy_id: int, version_id: int):
        """Fine-grained invalidation: purge only cache entries touching the specific policy version."""
        keys_to_remove = []
        for key, item in list(self._local_l1.items()):
            if version_id in item.get("version_ids", []) or (policy_id in item.get("policy_ids", []) and not item.get("version_ids")):
                keys_to_remove.append(key)
        for key in keys_to_remove:
            self._local_l1.pop(key, None)

        for sk in list(self._local_l2.keys()):
            self._local_l2[sk] = [
                item for item in self._local_l2[sk]
                if version_id not in item.get("version_ids", []) and not (policy_id in item.get("policy_ids", []) and not item.get("version_ids"))
            ]
        logger.info(f"Targeted invalidation for version {policy_id}:{version_id}: removed {len(keys_to_remove)} L1 entries")

    def clear(self):
        """Purge all cached entries across L1 and L2."""
        self._local_l1.clear()
        self._local_l2.clear()
        if self.use_redis:
            try:
                self.redis.flushdb()
            except Exception as e:
                logger.warning(f"Redis flushdb failed in cache clear: {e}")

_CACHE = None
def get_cache() -> MultiLevelCache:
    global _CACHE
    if _CACHE is None:
        _CACHE = MultiLevelCache()
    return _CACHE
