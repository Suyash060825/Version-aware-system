"""
rag/vectordb/chroma.py
ChromaDB vector store with embedding model isolation and dimension safety.
"""
import os
import logging
from typing import List, Dict, Optional, Any
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
        
        # Isolate collection per embedding model to prevent dimension mismatch
        from rag.embeddings.embedder import get_embedder
        embedder = get_embedder()
        self.embedding_model = getattr(embedder, "model_name", os.environ.get("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5"))
        self.embedding_dimension = getattr(embedder, "dimension", 384)
        self.embedding_revision = "1.0.0"

        safe_model_slug = self.embedding_model.split("/")[-1].replace("-", "_").replace(".", "_").lower()
        self.col_name = f"policy_chunks_{safe_model_slug}"

        try:
            self._col = self._client.get_or_create_collection(
                name=self.col_name,
                metadata={
                    "hnsw:space": "cosine",
                    "embedding_model": self.embedding_model,
                    "embedding_dimension": self.embedding_dimension,
                    "embedding_revision": self.embedding_revision
                }
            )
            # Verify stored metadata against runtime
            col_meta = self._col.metadata or {}
            stored_dim = col_meta.get("embedding_dimension")
            stored_model = col_meta.get("embedding_model")
            if stored_dim is not None and int(stored_dim) != self.embedding_dimension:
                logger.error(
                    f"Dimension mismatch in {self.col_name}: expected {self.embedding_dimension}, found {stored_dim}. Rebuilding collection."
                )
                self._client.delete_collection(name=self.col_name)
                self._col = self._client.create_collection(
                    name=self.col_name,
                    metadata={
                        "hnsw:space": "cosine",
                        "embedding_model": self.embedding_model,
                        "embedding_dimension": self.embedding_dimension,
                        "embedding_revision": self.embedding_revision
                    }
                )
        except Exception as e:
            logger.warning(f"Collection {self.col_name} error: {e}. Recreating...")
            try:
                self._client.delete_collection(name=self.col_name)
            except Exception:
                pass
            self._col = self._client.create_collection(
                name=self.col_name,
                metadata={
                    "hnsw:space": "cosine",
                    "embedding_model": self.embedding_model,
                    "embedding_dimension": self.embedding_dimension,
                    "embedding_revision": self.embedding_revision
                }
            )

    def upsert_chunks(self, chunks: List[dict], embeddings: List[List[float]]):
        if not chunks or not embeddings:
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
            
        try:
            self._col.upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)
        except Exception as e:
            logger.error(f"Error upserting into Chroma {self.col_name}: {e}. Rebuilding collection.")
            self._client.delete_collection(name=self.col_name)
            self._col = self._client.create_collection(name=self.col_name, metadata={"hnsw:space": "cosine"})
            self._col.upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)

    def delete_policy_version(self, policy_id: int, version: str):
        try:
            results = self._col.get(where={"$and": [
                {"policy_id": {"$eq": str(policy_id)}},
                {"version": {"$eq": str(version)}},
            ]})
            if results and results["ids"]:
                self._col.delete(ids=results["ids"])
        except Exception:
            pass

    def delete_policy(self, policy_id: int):
        try:
            results = self._col.get(where={"policy_id": {"$eq": str(policy_id)}})
            if results and results["ids"]:
                self._col.delete(ids=results["ids"])
        except Exception:
            pass

    def search(self, embedding: List[float], filters: dict, top_k: int = 50) -> List[dict]:
        if embedding and len(embedding) != self.embedding_dimension:
            raise ValueError(
                f"Embedding dimension mismatch: query vector has {len(embedding)} dimensions, "
                f"but vector store '{self.col_name}' requires {self.embedding_dimension} dimensions ({self.embedding_model})."
            )
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
        except Exception as e:
            logger.error(f"Chroma query failed: {e}")
            return []
            
        hits = []
        if results and results["ids"] and len(results["ids"]) > 0:
            for i, doc_id in enumerate(results["ids"][0]):
                meta = dict(results["metadatas"][0][i])
                meta["id"] = doc_id
                meta["chunk_id"] = doc_id
                meta["text"] = results["documents"][0][i]
                meta["score"] = max(0.0, 1.0 - float(results["distances"][0][i]))
                hits.append(meta)
        return hits

    def _build_where(self, filters: dict):
        if not filters:
            return None
        conditions = []
        for k, v in filters.items():
            if isinstance(v, list):
                conditions.append({k: {"$in": [str(x) for x in v]}})
            else:
                conditions.append({k: {"$eq": str(v)}})
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
            "collection": self.col_name,
            "path": CHROMA_PATH,
            "model": "chromadb",
        }

_store = None
def get_store() -> VectorStoreBase:
    global _store
    if _store is None:
        _store = VectorStore()
    return _store
