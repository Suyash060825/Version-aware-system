"""
Module 27: Version-Scoped Semantic Cache
Provides a semantic cache for RAG answers that respects policy version drift.
"""
import json
import os
import numpy as np
import redis
import hashlib
from typing import List, Dict, Any, Optional

CACHE_THRESHOLD = float(os.environ.get("CACHE_THRESHOLD", 0.95))
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

class SemanticCache:
    def __init__(self):
        self.use_redis = False
        try:
            self.redis = redis.from_url(REDIS_URL)
            self.redis.ping()
            self.use_redis = True
        except Exception:
            self.redis = None
            self.local_cache = []

    def _cosine_similarity(self, a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    def _get_active_versions(self, policy_ids: List[int]) -> Dict[int, int]:
        from models import PolicyVersion
        active_versions = PolicyVersion.query.filter(
            PolicyVersion.policy_id.in_(policy_ids),
            PolicyVersion.is_active == True
        ).all()
        return {v.policy_id: v.id for v in active_versions}
        
    def _get_chunk_hashes(self, policy_ids: List[int], version_ids: List[int]) -> set:
        from models import PolicyChunk
        chunks = PolicyChunk.query.filter(
            PolicyChunk.policy_id.in_(policy_ids),
            PolicyChunk.version_id.in_(version_ids)
        ).all()
        return {hashlib.sha256(c.text_preview.encode()).hexdigest() for c in chunks}

    def _hash_citations(self, citations: List[Dict]) -> set:
        # Instead of getting from DB, we hash the texts that were actually cited.
        # But wait, citations might not contain text_preview, it contains 'text' or 'content'.
        hashes = set()
        for c in citations:
            text = c.get('text', c.get('content', ''))
            # Hash first 300 chars to match text_preview
            hashes.add(hashlib.sha256(text[:300].encode()).hexdigest())
        return hashes

    def get(self, query_embedding: List[float], allowed_depts: Optional[List[str]] = None, is_diff_query: bool = False) -> Optional[Dict]:
        best_match = None
        best_score = -1.0
        best_key = None

        dept_str = json.dumps(sorted(allowed_depts)) if allowed_depts else "none"

        if self.use_redis:
            keys = self.redis.keys("vssc:*")
            for k in keys:
                data = self.redis.get(k)
                if data:
                    entry = json.loads(data)
                    if entry.get("allowed_depts") != dept_str or entry.get("is_diff_query") != is_diff_query:
                        continue
                    score = self._cosine_similarity(query_embedding, entry["embedding"])
                    if score > best_score:
                        best_score = score
                        best_match = entry
                        best_key = k
        else:
            for i, entry in enumerate(self.local_cache):
                if entry.get("allowed_depts") != dept_str or entry.get("is_diff_query") != is_diff_query:
                    continue
                score = self._cosine_similarity(query_embedding, entry["embedding"])
                if score > best_score:
                    best_score = score
                    best_match = entry
                    best_key = i

        if best_match and best_score >= CACHE_THRESHOLD:
            # Check version drift
            cited_policies = best_match.get("cited_policies", {})
            if not cited_policies:
                return best_match

            policy_ids = [int(pid) for pid in cited_policies.keys()]
            active_versions = self._get_active_versions(policy_ids)
            
            is_valid = True
            for pid, vid in cited_policies.items():
                if active_versions.get(int(pid)) != vid:
                    is_valid = False
                    break
                    
            if not is_valid:
                from rag.metrics import CACHE_INVALIDATIONS, CACHE_MISSES
                CACHE_INVALIDATIONS.labels(reason="version_drift").inc()
                CACHE_MISSES.labels(reason="version_drift").inc()
                # Invalidate it
                if self.use_redis:
                    self.redis.delete(best_key)
                else:
                    self.local_cache.pop(best_key)
                return None
                
            from rag.metrics import CACHE_HITS
            CACHE_HITS.inc()
            return best_match
            
        from rag.metrics import CACHE_MISSES
        CACHE_MISSES.labels(reason="not_found").inc()
        return None

    def put(self, query_embedding: List[float], answer: str, citations: List[Dict], chunks_used: int, allowed_depts: Optional[List[str]] = None, model: str = "cache", is_diff_query: bool = False):
        cited_policies = {}
        for c in citations:
            pid = c.get("policy_id")
            vid = c.get("version_id")
            if pid and vid:
                cited_policies[pid] = vid
                
        chunk_hashes = list(self._hash_citations(citations))
        dept_str = json.dumps(sorted(allowed_depts)) if allowed_depts else "none"

        entry = {
            "embedding": query_embedding,
            "answer": answer,
            "citations": citations,
            "chunks_used": chunks_used,
            "allowed_depts": dept_str,
            "cited_policies": cited_policies,
            "chunk_hashes": chunk_hashes,
            "model": model,
            "is_diff_query": is_diff_query
        }

        if self.use_redis:
            key_id = hashlib.sha256(np.array(query_embedding).tobytes()).hexdigest()
            self.redis.set(f"vssc:{key_id}", json.dumps(entry))
        else:
            self.local_cache.append(entry)

    def invalidate_for_policy(self, policy_id: int, active_version_id: int):
        """Invalidate entries that cite this policy but NOT the current active_version_id."""
        from rag.metrics import CACHE_INVALIDATIONS
        count = 0
        if self.use_redis:
            keys = self.redis.keys("vssc:*")
            for k in keys:
                data = self.redis.get(k)
                if data:
                    entry = json.loads(data)
                    cited = entry.get("cited_policies", {})
                    if str(policy_id) in cited and cited[str(policy_id)] != active_version_id:
                        self.redis.delete(k)
                        count += 1
        else:
            new_cache = []
            for entry in self.local_cache:
                cited = entry.get("cited_policies", {})
                if str(policy_id) in cited and cited[str(policy_id)] != active_version_id:
                    count += 1
                    continue
                new_cache.append(entry)
            self.local_cache = new_cache
            
        if count > 0:
            CACHE_INVALIDATIONS.labels(reason="explicit_drift").inc(count)
        return count

_cache_instance = None

def get_cache():
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = SemanticCache()
    return _cache_instance
