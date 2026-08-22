import os
os.environ["FLASK_ENV"] = "development"
from app import create_app
app = create_app()
with app.app_context():
    from rag.vectordb.chroma import get_store
    store = get_store()
    print("Store count:", store.count())
    where = store._build_where(None, None, True, ["Human Resources", ""])
    print("Where filter:", where)
    try:
        results = store._col.query(
            query_embeddings=[[0.0]*384],
            n_results=5,
            where=where,
            include=["documents", "metadatas", "distances"]
        )
        print("Query success! Found docs:", len(results.get("ids", [[]])[0]))
    except Exception as e:
        import traceback
        traceback.print_exc()
