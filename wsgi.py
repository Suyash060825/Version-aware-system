import os
from app import create_app

env = os.environ.get("FLASK_ENV", "production")
application = create_app(env)

# Preload heavy QueryEngine models (embedder, reranker, NLI) in master process
# so worker forks share memory via copy-on-write (COW) and avoid cold-start delays.
if os.environ.get("PRELOAD_MODELS", "true").lower() == "true":
    try:
        from rag.engine.query_engine import get_query_engine
        get_query_engine()
    except Exception as e:
        import logging
        logging.getLogger("wsgi").warning(f"QueryEngine preloading warning: {e}")

