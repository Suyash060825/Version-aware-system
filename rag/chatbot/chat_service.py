"""
rag/chatbot/chat_service.py
Compatibility facade delegating directly to the authoritative QueryEngine.
Maintains legacy API signature for backward compatibility without duplicating retrieval or LLM logic.
"""
from typing import Optional, Dict, Any
from config import Config
from rag.engine.query_engine import get_query_engine

def answer(
    query: str,
    session_id: Optional[str] = None,
    user_role: str = "employee",
    user_department: str = "",
    top_k_retrieve: int = 20,
    top_k_rerank: int = 5,
    stream: bool = False,
    user: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Authoritative RAG pipeline compatibility facade.
    Delegates all retrieval, reranking, routing, and answering to QueryEngine.
    """
    engine = get_query_engine()

    # Resolve or create user proxy representation if raw role/dept strings passed
    if user is None:
        user = type('UserProxy', (), {
            'id': session_id or 0,
            'role': user_role,
            'department': type('DeptProxy', (), {'name': user_department, 'id': None})() if user_department else None,
            'department_id': None,
            'is_admin': lambda self: self.role.lower() == "admin",
            'is_hr': lambda self: self.role.lower() in ("admin", "hr"),
            'can_manage_policies': lambda self: self.role.lower() in ("admin", "hr", "manager"),
            'allowed_policy_ids': None,
        })()

    if stream:
        def stream_generator():
            full_ans = ""
            final_data = None
            for event in engine.stream_answer(query, user=user, session_id=session_id):
                if event.get("type") == "token":
                    full_ans += event.get("token", "")
                    yield {"token": event.get("token", "")}
                elif event.get("type") == "done":
                    final_data = event.get("result", {})
                    conf_raw = final_data.get("confidence", 1.0)
                    legacy_payload = {
                        "answer": final_data.get("answer", full_ans),
                        "citations": final_data.get("citations", []),
                        "chunks_used": len(final_data.get("citations", [])),
                        "session_id": session_id,
                        "fallback": final_data.get("fallback", False),
                        "model": final_data.get("model") or getattr(engine, "_model_name", getattr(Config, "LOCAL_LLM_MODEL", "qwen3")),
                        "cache_hit": False,
                        "confidence": int(conf_raw * 100) if conf_raw <= 1.0 else int(conf_raw),
                        "route": final_data.get("route", "HYBRID_RAG"),
                        "usage": {}
                    }
                    yield {"final": legacy_payload}
        return stream_generator()

    result = engine.answer(query, user=user, session_id=session_id)

    return {
        "answer": result.answer,
        "citations": result.citations,
        "chunks_used": result.retrieval_count,
        "session_id": session_id,
        "fallback": result.abstained,
        "model": result.model or getattr(engine, "_model_name", getattr(Config, "LOCAL_LLM_MODEL", "qwen3")),
        "cache_hit": getattr(result, "cache_hit", False),
        "confidence": int(result.confidence * 100) if result.confidence <= 1.0 else int(result.confidence),
        "usage": {},
        "route": result.route
    }
