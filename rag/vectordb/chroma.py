import os
import logging
from typing import List, Dict, Optional
from abc import ABC, abstractmethod
import chromadb

logger = logging.getLogger(__name__)

class VectorStoreBase(ABC):
    @abstractmethod
    def upsert_chunks(self, chunks: List[dict], embeddings: List[List[float]]): pass
    @abstractmethod
    def delete_policy(self, policy_id: int): pass
    @abstractmethod
    def delete_policy_version(self, policy_id: int, version: str): pass
    @abstractmethod
    def search(self, embedding: List[float], filters: dict, top_k: int) -> List[dict]: pass
    @abstractmethod
    def stats(self) -> dict: pass

CHROMA_PATH = "data/chroma"

class VectorStore(VectorStoreBase):
    def __init__(self, path: str = CHROMA_PATH):
        os.makedirs(path, exist_ok=True)
        self._client = chromadb.PersistentClient(path=path)
        self._col = self._client.get_or_create_collection(
            name="policy_chunks", metadata={"hnsw:space": "cosine"}
        )

    def upsert_chunks(self, chunks: List[dict], embeddings: List[List[float]]):
        if not chunks:
            return
        ids = [c["chunk_id"] if "chunk_id" in c else f"chunk_{c.get('policy_id')}_{c.get('version')}_{c.get('chunk_index')}" for c in chunks]
        
        documents = [c.get("text", "") for c in chunks]
        metadatas = []
        for c in chunks:
            m = {}
            for k, v in c.items():
                if k != "text" and v is not None:
                    m[k] = str(v) if not isinstance(v, (str, int, float, bool)) else v
            metadatas.append(m)
            
        self._col.upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)

    def delete_policy_version(self, policy_id: int, version: str):
        try:
            results = self._col.get(where={"$and": [
                {"policy_id": {"$eq": str(policy_id)}},
                {"version": {"$eq": str(version)}},
            ]})
            if results["ids"]:
                self._col.delete(ids=results["ids"])
        except Exception:
            pass

    def delete_policy(self, policy_id: int):
        try:
            results = self._col.get(where={"policy_id": {"$eq": str(policy_id)}})
            if results["ids"]:
                self._col.delete(ids=results["ids"])
        except Exception:
            pass

    def search(self, embedding: List[float], filters: dict, top_k: int = 50) -> List[dict]:
        where = self._build_where(filters)
        n_results = min(top_k, max(self._col.count(), 1))
        if n_results == 0:
            return []
            
        try:
            results = self._col.query(
                query_embeddings=[embedding],
                n_results=n_results,
                where=where if where else None,
                include=["documents", "metadatas", "distances"],
            )
        except Exception:
            return []
            
        hits = []
        if results and results["ids"]:
            for i, doc_id in enumerate(results["ids"][0]):
                meta = results["metadatas"][0][i]
                meta["id"] = doc_id
                meta["text"] = results["documents"][0][i]
                meta["score"] = max(0.0, 1.0 - results["distances"][0][i])
                hits.append(meta)
        return hits

    def _build_where(self, filters: dict):
        if not filters:
            return None
        conditions = []
        for k, v in filters.items():
            if isinstance(v, list):
                conditions.append({k: {"$in": v}})
            else:
                conditions.append({k: {"$eq": v}})
        if not conditions:
            return None
        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}

    def count(self) -> int:
        return self._col.count()

    def stats(self) -> dict:
        return {
            "total_chunks": self._col.count(),
            "collection": "policy_chunks",
            "path": CHROMA_PATH,
            "model": "chromadb",
        }

_store = None
def get_store() -> VectorStoreBase:
    global _store
    if _store is None:
        _store = VectorStore()
    return _store
