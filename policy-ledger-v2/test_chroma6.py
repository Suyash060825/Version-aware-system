import os
os.environ["FLASK_ENV"] = "development"
from app import create_app
from rag.vectordb.chroma import get_store

app = create_app()
with app.app_context():
    store = get_store()
    res = store._col.get(include=["metadatas"])
    print("Total documents in Chroma:", len(res['metadatas']))
    
    # Check what is_active is set to for Leave Policy
    for i in range(len(res['metadatas'])):
        meta = res['metadatas'][i]
        if 'Leave Policy' in str(meta):
            print(f"Meta: {meta}")
            break
