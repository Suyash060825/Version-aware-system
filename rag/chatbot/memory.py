"""rag/chatbot/memory.py - conversation store keyed by session_id"""
import json
import os
import redis
from datetime import datetime

MAX_TURNS = 10
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

_sessions = {}
_redis_client = None
try:
    _redis_client = redis.from_url(REDIS_URL)
    _redis_client.ping()
except Exception:
    _redis_client = None


def add_message(session_id: str, role: str, content: str):
    msg = {"role": role, "content": content, "time": datetime.now().isoformat()}
    if _redis_client:
        key = f"chat_mem:{session_id}"
        _redis_client.rpush(key, json.dumps(msg))
        # Trim list
        if _redis_client.llen(key) > MAX_TURNS * 2:
            _redis_client.lpop(key)
        _redis_client.expire(key, 86400) # 24h
    else:
        if session_id not in _sessions:
            _sessions[session_id] = []
        _sessions[session_id].append(msg)
        if len(_sessions[session_id]) > MAX_TURNS * 2:
            _sessions[session_id] = _sessions[session_id][-(MAX_TURNS * 2):]


def get_history(session_id: str) -> list[dict]:
    if _redis_client:
        key = f"chat_mem:{session_id}"
        msgs = _redis_client.lrange(key, 0, -1)
        return [json.loads(m) for m in msgs]
    return _sessions.get(session_id, [])


def clear_session(session_id: str):
    if _redis_client:
        _redis_client.delete(f"chat_mem:{session_id}")
    else:
        _sessions.pop(session_id, None)
