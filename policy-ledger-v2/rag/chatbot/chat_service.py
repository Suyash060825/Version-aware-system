"""
rag/chatbot/chat_service.py
Full RAG pipeline: question → embed → retrieve → rerank → prompt → LLM → cite
"""
from rag.embeddings.embedder import get_embedder
from rag.vectordb.chroma import get_store
from rag.reranker.reranker import get_reranker
from rag.llm.prompt_builder import build_prompt
from rag.llm.gemini import get_llm
from rag.chatbot.citations import build_citations, format_citations_text
from rag.chatbot.memory import get_history, add_message

RELEVANCE_THRESHOLD = 0.10


def answer(
    query: str,
    session_id: str,
    user_role: str = "employee",
    user_department: str = "",
    top_k_retrieve: int = 20,
    top_k_rerank: int = 5,
) -> dict:
    """
    Full pipeline. Returns:
    {
        "answer": str,
        "citations": list[dict],
        "chunks_used": int,
        "session_id": str,
        "fallback": bool,
    }
    """
    embedder = get_embedder()
    store = get_store()
    reranker = get_reranker()
    llm = get_llm()

    # Role-based department filtering
    allowed_depts = None
    if user_role == "employee" and user_department:
        allowed_depts = [user_department, ""]  # own dept + company-wide
    elif user_role in ("hr", "admin"):
        allowed_depts = None  # no restriction

    # 1. Embed query
    q_vec = embedder.embed_query(query)

    # 2. Retrieve top-N semantic matches
    hits = store.search(
        query_embedding=q_vec,
        query_text=query,
        top_k=top_k_retrieve,
        active_only=True,
        allowed_departments=allowed_depts,
    )

    # 3. Filter by relevance threshold
    hits = [h for h in hits if h.get("score", 0) >= RELEVANCE_THRESHOLD]

    if not hits:
        answer_text = "I couldn't find this information in the available policies."
        add_message(session_id, "user", query)
        add_message(session_id, "assistant", answer_text)
        return {
            "answer": answer_text,
            "citations": [],
            "chunks_used": 0,
            "session_id": session_id,
            "fallback": True,
        }

    # 4. Rerank
    top_chunks = reranker.rerank(query, hits, top_k=top_k_rerank)

    # 5. Build prompt with conversation memory
    history = get_history(session_id)
    messages = build_prompt(query, top_chunks, chat_history=history)

    # 6. Generate answer
    answer_text = llm.complete(messages)

    # 7. Citations
    citations = build_citations(top_chunks)

    # 8. Update memory
    add_message(session_id, "user", query)
    add_message(session_id, "assistant", answer_text)

    return {
        "answer": answer_text,
        "citations": citations,
        "chunks_used": len(top_chunks),
        "session_id": session_id,
        "fallback": False,
    }
