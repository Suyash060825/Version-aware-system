"""
rag/chatbot/self_healing.py
Self-healing feedback loop that patches semantic cache on negative user feedback.
"""
import os
import logging
from flask import has_app_context
from models import db, ChatMessage
from rag.llm_provider import get_llm_provider
from rag.cache.semantic_cache import get_cache
from rag.embeddings.embedder import get_embedder

logger = logging.getLogger("rag.chatbot.self_healing")

def _do_self_healing(msg_id: int):
    msg = db.session.get(ChatMessage, msg_id)
    if not msg or msg.role != "assistant":
        return
        
    # Find preceding user message
    user_msg = ChatMessage.query.filter(
        ChatMessage.session_id == msg.session_id,
        ChatMessage.role == "user",
        ChatMessage.created_at < msg.created_at
    ).order_by(ChatMessage.created_at.desc()).first()
    
    if not user_msg:
        return
        
    query = user_msg.content
    bad_answer = msg.content
    
    # Analyze failure and generate better answer
    from rag.vectordb.chroma import get_store
    store = get_store()
    embedder = get_embedder()
    q_vec = embedder.embed_query(query)
    
    hits = store.search(q_vec, filters={"is_active": True}, top_k=10)
    if not hits:
        return
    context = "\n\n".join([h.get("text", "") for h in hits[:5]])
    
    prompt = f"""You are an Auto-Finetuning & Self-Healing Agent.
A user asked: "{query}"
The previous AI answered: "{bad_answer}"
The user gave this a thumbs down.

Here is the retrieved context from the database:
{context}

Please write a corrected, highly accurate answer to the user's question based strictly on the context. If the context does not contain the answer, say "I couldn't find sufficient information".
"""

    provider = get_llm_provider()
    messages = [
        {"role": "system", "content": "You are a self-healing diagnostic system."},
        {"role": "user", "content": prompt}
    ]
    
    try:
        resp = provider.generate(messages)
        corrected_answer = resp.text if hasattr(resp, "text") else str(resp)
        if not corrected_answer or "insufficient information" in corrected_answer.lower():
            return

        from rag.verification.entailment import EntailmentVerifier
        verifier = EntailmentVerifier()
        is_grounded, _ = verifier.verify(corrected_answer, hits[:5])
        if not is_grounded:
            logger.info(f"[Self-Healing] Corrected answer failed entailment check; aborting cache patch.")
            return
            
        from rag.chatbot.citations import build_citations
        from rag.authorization.citation_validator import CitationValidator
        from rag.engine.query_scope import QueryScope

        raw_citations = build_citations(hits[:5]) if hits else []
        real_citations = CitationValidator().validate_and_enrich(raw_citations) if raw_citations else []
        
        # Inject into Semantic Cache only with verified real citations and scope
        if real_citations:
            cache = get_cache()
            scope = QueryScope.from_user(getattr(user_msg, "user", None)) if hasattr(user_msg, "user") else None
            cache.put(
                query_embedding=q_vec,
                answer=corrected_answer,
                citations=real_citations,
                chunks_used=len(real_citations),
                scope=scope,
                model="self-healed",
                confidence=0.85,
                query=query
            )
            logger.info(f"[Self-Healing] Successfully patched cache with authoritative evidence for query: {query}")
    except Exception as e:
        logger.warning(f"[Self-Healing] Failed: {e}")

def trigger_self_healing(msg_id: int):
    if has_app_context():
        _do_self_healing(msg_id)
    else:
        from app import create_app
        env = os.environ.get("FLASK_ENV", "production")
        app = create_app(env)
        with app.app_context():
            _do_self_healing(msg_id)
