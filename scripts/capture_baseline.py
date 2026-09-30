import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app
from models import db, PolicyChunkV2
import redis

app = create_app('production')
with app.app_context():
    print("Database URL:", app.config.get('SQLALCHEMY_DATABASE_URI'))
    
    try:
        print("Chunk Count DB:", db.session.query(PolicyChunkV2).count())
    except Exception as e:
        print("Chunk Count DB: Error", e)
        
    try:
        from rag.retrieval.sparse import PersistentBM25Index
        idx = PersistentBM25Index()
        print("BM25 Count:", len(idx.doc_texts))
    except Exception as e:
        print("BM25 Count: ERROR", e)

    try:
        from rag.retrieval.dense import get_dense_retriever
        dense = get_dense_retriever()
        print("FAISS Count:", dense.index.ntotal if hasattr(dense, 'index') and dense.index else "Unknown")
        print("Chroma Count:", dense.collection.count() if hasattr(dense, 'collection') else "Unknown")
    except Exception as e:
        print("Dense Count: ERROR", e)
        
    try:
        r = redis.Redis.from_url(app.config.get('REDIS_URL', 'redis://localhost:6379/0'))
        r.ping()
        print("Redis: Connected")
    except Exception as e:
        print("Redis:", e)
