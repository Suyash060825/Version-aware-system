from rag.vectordb.chroma import get_store
store = get_store()
data = store._col.get(limit=5)
print("Sample Metadata:")
for m in data['metadatas']:
    print(m)
