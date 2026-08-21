import json
from models import db, ChatMessage
from rag.llm_provider import get_llm_provider
from rag.cache.semantic_cache import get_cache
from rag.embeddings.embedder import get_embedder

def trigger_self_healing(msg_id: int):
    import os
    from app import create_app  # deferred to avoid circular import at module load
    env = os.environ.get("FLASK_ENV", "development")
    app = create_app(env)
    with app.app_context():
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
        
        hits = store.search(q_vec, query, top_k=10, active_only=True)
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
            corrected_answer = resp.text
            
            # Extract policy IDs to ensure cache invalidation works later if needed
            policy_ids = {h.get("policy_id") for h in hits[:5] if h.get("policy_id")}
            
            # Inject into Semantic Cache to act as a "corrected anchor" for future queries
            cache = get_cache()
            
            # Reconstruct dummy citations with actual policy IDs and active version IDs to participate in version invalidation
            from models import PolicyVersion
            citations = []
            for h in hits[:5]:
                pid = h.get("policy_id")
                if pid:
                    ver = PolicyVersion.query.filter_by(policy_id=pid, is_active=True).first()
                    vid = ver.id if ver else None
                    citations.append({"policy_id": pid, "version_id": vid, "title": h.get("title", "Self-Healed")})
            
            cache.put(
                query_embedding=q_vec,
                answer=corrected_answer,
                citations=citations,
                chunks_used=len(hits[:5]),
                allowed_depts=None,
                model="self-healed",
                is_diff_query=False
            )
            print(f"[Self-Healing] Successfully patched cache for query: {query}")
        except Exception as e:
            print("[Self-Healing] Failed:", e)
