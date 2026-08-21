from rag.vectordb.chroma import get_store
store = get_store()
print(store._col.metadata)
