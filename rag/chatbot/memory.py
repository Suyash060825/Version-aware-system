"""rag/chatbot/memory.py - in-memory conversation store keyed by session_id with LRU eviction and thread-safety"""
from datetime import datetime
from collections import OrderedDict
import threading

_sessions: OrderedDict = OrderedDict()
_lock = threading.Lock()
MAX_TURNS = 10
MAX_SESSIONS = 5000


def add_message(session_id: str, role: str, content: str):
    if not session_id:
        return
    with _lock:
        if session_id in _sessions:
            history = _sessions[session_id]
            _sessions.move_to_end(session_id)
        else:
            if len(_sessions) >= MAX_SESSIONS:
                _sessions.popitem(last=False)
            history = []
            _sessions[session_id] = history

        history.append({"role": role, "content": content, "time": datetime.now().isoformat()})
        if len(history) > MAX_TURNS * 2:
            _sessions[session_id] = history[-(MAX_TURNS * 2):]


def get_history(session_id: str) -> list[dict]:
    if not session_id:
        return []
    with _lock:
        if session_id in _sessions:
            _sessions.move_to_end(session_id)
            return list(_sessions[session_id])
        return []


def clear_session(session_id: str):
    if not session_id:
        return
    with _lock:
        _sessions.pop(session_id, None)
