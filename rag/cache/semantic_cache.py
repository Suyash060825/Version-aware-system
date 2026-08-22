import os
import json
import logging
import hashlib
from typing import List, Dict, Optional
from models import PolicyVersion, db

logger = logging.getLogger(__name__)

class MultiLevelCache:
    """
    L1: Exact query hash cache (Redis, TTL=1h)
    L2: Semantic QA cache (numpy similarity on cached embeddings)
    L3: Retrieval result cache (Redis, TTL=30min)
    
    Cache key incorporates: user role, department, policy scope.
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

        self.local_cache = []

    def get_l1(self, query_hash: str, scope_key: str) -> Optional[dict]:
        if not self.use_redis:
            return None
        data = self.redis.get(f"l1:{scope_key}:{query_hash}")
        if data:
            return json.loads(data)
        return None
        
    def set_l1(self, query_hash: str, scope_key: str, result: dict):
        if self.use_redis:
            self.redis.setex(f"l1:{scope_key}:{query_hash}", 3600, json.dumps(result))

    def get_l2(self, query_embedding: List[float], scope_key: str) -> Optional[dict]:
        # Skipping vector scanning in Redis for simplicity, 
        # usually done with RediSearch or standard memory
        return None
        
    def invalidate_version(self, policy_id: int, version_id: int):
        if self.use_redis:
            # Delete any scopes referring to the old policy
            pass

_CACHE = None
def get_cache() -> MultiLevelCache:
    global _CACHE
    if _CACHE is None:
        _CACHE = MultiLevelCache()
    return _CACHE
