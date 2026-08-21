from app import create_app
import os
os.environ["FLASK_ENV"] = "development"
app = create_app("development")
with app.app_context():
    from rag.chatbot.chat_service import get_store, get_embedder
    embedder = get_embedder()
    store = get_store()
    query = "remote work"
    q_vec = embedder.embed_query(query)
    hits = store.search(
        query_embedding=q_vec,
        query_text=query,
        top_k=5,
        active_only=True,
        allowed_departments=None,
    )
    print("Hits count:", len(hits))
    if hits:
        print("First hit score:", hits[0].get("score"))
