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

    def delete_policy_version(self, policy_id: int, version: Any):
        try:
            p_val = int(policy_id) if str(policy_id).isdigit() else policy_id
            v_int = int(version) if str(version).isdigit() else None
            v_str = str(version)

            all_results = []
            res_int = self._col.get(where={"policy_id": {"$eq": p_val}})
            if res_int and res_int.get("ids"):
                all_results.append(res_int)
            if str(p_val) != p_val:
                res_str = self._col.get(where={"policy_id": {"$eq": str(p_val)}})
                if res_str and res_str.get("ids"):
                    all_results.append(res_str)

            to_delete = set()
            for results in all_results:
                for idx, m in enumerate(results.get("metadatas", [])):
                    m_vid = m.get("version_id")
                    m_ver = str(m.get("version", ""))
                    if (v_int is not None and m_vid == v_int) or m_ver == v_str or str(m_vid) == v_str:
                        to_delete.add(results["ids"][idx])
            if to_delete:
                self._col.delete(ids=list(to_delete))
        except Exception as e:
            logger.error(f"Failed to delete policy {policy_id} version {version} from Chroma: {e}")

    def delete_policy(self, policy_id: int):
        try:
            p_val = int(policy_id) if str(policy_id).isdigit() else policy_id
            ids_to_del = set()
            res_int = self._col.get(where={"policy_id": {"$eq": p_val}})
            if res_int and res_int.get("ids"):
                ids_to_del.update(res_int["ids"])
            if str(p_val) != p_val:
                res_str = self._col.get(where={"policy_id": {"$eq": str(p_val)}})
                if res_str and res_str.get("ids"):
                    ids_to_del.update(res_str["ids"])
            if ids_to_del:
                self._col.delete(ids=list(ids_to_del))
        except Exception as e:
            logger.error(f"Failed to delete policy {policy_id} from Chroma: {e}")

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
                if "policy_id" in meta and meta["policy_id"] is not None:
                    try:
                        meta["policy_id"] = int(meta["policy_id"])
                    except (ValueError, TypeError):
                        pass
                if "version_id" in meta and meta["version_id"] is not None:
                    try:
                        meta["version_id"] = int(meta["version_id"])
                    except (ValueError, TypeError):
                        pass
                if "page" in meta and meta["page"] is not None:
                    try:
                        meta["page"] = int(meta["page"])
                    except (ValueError, TypeError):
                        pass
                hits.append(meta)
        return hits

    def _build_where(self, filters: dict):
        if not filters:
            return None
        conditions = []
        for k, v in filters.items():
            if k in ("$and", "$or"):
                conditions.append({k: v})
            elif isinstance(v, dict):
                conditions.append({k: v})
            elif isinstance(v, (list, tuple, set)):
                conditions.append({k: {"$in": list(v)}})
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
