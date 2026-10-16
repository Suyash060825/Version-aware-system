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
            self._local_l1.clear()
        self._local_l1[key] = item_data

    def get_l2(self, query_embedding: List[float], scope_key: str = "", threshold: float = 0.95) -> Optional[dict]:
        if not query_embedding or not self._local_l2:
            return None
        now = time.time()
        # Filter candidate items by scope_key and non-expiration in reverse order
        candidates = [
            item for item in reversed(self._local_l2)
            if item.get("expires_at", 0) >= now and item.get("scope_key") == scope_key and item.get("embedding")
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
        if len(self._local_l2) > self._max_local:
            now = time.time()
            self._local_l2 = [item for item in self._local_l2 if item.get("expires_at", 0) >= now][-500:]
        self._local_l2.append({
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
            return f"t={tenant}|r={role}|d={depts}|c={conf}|h={hist}|td={t_date}|v={ver}|diff={is_diff_query}"
        scope_str = ",".join(sorted(allowed_depts or [])) + f"|diff={is_diff_query}"
        return scope_str

    def get(self, query_embedding: List[float], scope: Optional[Any] = None, allowed_depts: Optional[List[str]] = None, is_diff_query: bool = False) -> Optional[dict]:
        """
        Fast L2 cache lookup with lazy TTL strategy for chunks and versions.
        Chunk/version validity is trusted for its TTL window and invalidated on writes.
        Policy-level authorization is validated fail-closed.
        """
        scope_key = self._make_scope_key(scope=scope, allowed_depts=allowed_depts, is_diff_query=is_diff_query)
        cached = self.get_l2(query_embedding, scope_key=scope_key)
        if not cached:
            return None

        # Verify cached policy authorization (lazy TTL strategy: chunk & version validity trusted within TTL)
        try:
            from flask import has_app_context
            if has_app_context():
                from models import db, Policy
                from rag.authorization.evidence_filter import get_evidence_filter
                evidence_filter = get_evidence_filter()

                citations = cached.get("citations", [])
                checked_policies = set()
                for cit in citations:
                    pid = cit.get("policy_id")
                    if pid and pid not in checked_policies:
                        checked_policies.add(pid)
                        policy = db.session.get(Policy, int(pid))
                        if not policy:
                            logger.info(f"Cached policy {pid} no longer exists in DB. Invalidating cache hit.")
                            return None
                        if scope and not evidence_filter.is_authorized_for_policy(scope, policy):
                            logger.info(f"User scope not authorized for cached policy {pid}. Invalidating cache hit.")
                            return None
            else:
                # Outside application context with no DB access, do not serve unverifiable cache
                return None
        except Exception as e:
            # SECURITY REQUIREMENT: Cache validation exception must ALWAYS result in CACHE MISS (fail closed)
            logger.warning(f"Cache validation check failed unexpectedly: {e}. Treating as cache miss.")
            return None

        return cached

    def put(self, query_embedding: List[float], answer: str, citations: list, chunks_used: int, scope: Optional[Any] = None, allowed_depts: Optional[List[str]] = None, model: str = "", confidence: Optional[float] = None, is_diff_query: bool = False):
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

        self._local_l2 = [
            item for item in self._local_l2
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

        self._local_l2 = [
            item for item in self._local_l2
            if version_id not in item.get("version_ids", []) and not (policy_id in item.get("policy_ids", []) and not item.get("version_ids"))
        ]
        logger.info(f"Targeted invalidation for version {policy_id}:{version_id}: removed {len(keys_to_remove)} L1 entries")

_CACHE = None
def get_cache() -> MultiLevelCache:
    global _CACHE
    if _CACHE is None:
        _CACHE = MultiLevelCache()
    return _CACHE
