"""
rag/vectordb/chroma.py
ChromaDB wrapper for persistent vector storage.

Features:
- Persistent on disk (data/chroma/)
- Role-aware filtering (employee only sees their dept + public)
- Version-aware filtering (only latest active version by default)
- Hybrid search: semantic + keyword BM25-style boost
- Upsert-safe (same chunk can be re-indexed without duplicates)
"""
import os
from typing import Optional

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "chroma")


def _get_client():
    try:
        import chromadb
        os.makedirs(CHROMA_PATH, exist_ok=True)
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        return client
    except ImportError:
        raise ImportError("chromadb not installed. Run: pip install chromadb")


def _get_collection(client=None):
    if client is None:
        client = _get_client()
    return client.get_or_create_collection(
        name="policy_chunks",
        metadata={"hnsw:space": "cosine"},
    )


class VectorStore:
    def __init__(self):
        self._client = _get_client()
        self._col = _get_collection(self._client)

    # ----------------------------------------------------------------
    # Indexing
    # ----------------------------------------------------------------
    def upsert_chunks(
        self,
        chunks: list[dict],
        embeddings: list[list[float]],
    ):
        """
        Store chunks with their embeddings.
        chunk dict must contain: text, policy_id, policy_name, version,
        department, section, page, chunk_index
        """
        ids = [f"pol{c['policy_id']}_v{c['version']}_c{c['chunk_index']}" for c in chunks]
        documents = [c["text"] for c in chunks]
        metadatas = [
            {
                "policy_id": str(c.get("policy_id", "")),
                "policy_name": c.get("policy_name", ""),
                "version": str(c.get("version", "")),
                "department": c.get("department", ""),
                "section": c.get("section", "General"),
                "page": str(c.get("page", "")),
                "chunk_index": str(c.get("chunk_index", 0)),
                "is_active": str(c.get("is_active", True)),
            }
            for c in chunks
        ]
        self._col.upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)
        self._bm25_index = None

    def delete_policy_version(self, policy_id: int, version: str):
        """Remove all chunks for a specific policy version."""
        try:
            results = self._col.get(where={"$and": [
                {"policy_id": {"$eq": str(policy_id)}},
                {"version": {"$eq": str(version)}},
            ]})
            if results["ids"]:
                self._col.delete(ids=results["ids"])
                self._bm25_index = None
        except Exception:
            pass

    def delete_policy(self, policy_id: int):
        """Remove all chunks for a policy (all versions)."""
        try:
            results = self._col.get(where={"policy_id": {"$eq": str(policy_id)}})
            if results["ids"]:
                self._col.delete(ids=results["ids"])
                self._bm25_index = None
        except Exception:
            pass

    # ----------------------------------------------------------------
    # Retrieval
    # ----------------------------------------------------------------
    def search(
        self,
        query_embedding: list[float],
        query_text: str,
        top_k: int = 20,
        policy_id: Optional[int] = None,
        department: Optional[str] = None,
        active_only: bool = True,
        allowed_departments: Optional[list[str]] = None,
    ) -> list[dict]:
        """
        Hybrid search: semantic (via ChromaDB cosine) + keyword boost.

        Filters applied:
        - active_only: skip superseded versions
        - department: restrict to specific department
        - allowed_departments: role-based whitelist
        """
        where = self._build_where(policy_id, department, active_only, allowed_departments)
        n_results = min(top_k, max(self._col.count(), 1))

        try:
            results = self._col.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where if where else None,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            return []

        hits = []
        
        # Build lazy BM25 index if not built or if corpus changed
        if not hasattr(self, "_bm25_index") or self._bm25_index is None:
            all_docs = self._col.get(include=["documents", "metadatas"])
            self._bm25_ids = all_docs["ids"]
            self._bm25_docs = all_docs["documents"]
            self._bm25_metas = all_docs["metadatas"]
            tokenized_corpus = [doc.lower().split() for doc in self._bm25_docs]
            from rank_bm25 import BM25Okapi
            self._bm25_index = BM25Okapi(tokenized_corpus) if tokenized_corpus else None
            
        semantic_ranks = {}
        for i, doc_id in enumerate(results["ids"][0]):
            semantic_ranks[doc_id] = {
                "rank": i + 1,
                "score": max(0.0, 1.0 - results["distances"][0][i]),
                "text": results["documents"][0][i],
                "meta": results["metadatas"][0][i]
            }
            
        bm25_ranks = {}
        if self._bm25_index:
            query_tokens = query_text.lower().split()
            bm25_scores = self._bm25_index.get_scores(query_tokens)
            # Sort all indices by score
            top_bm25_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)
            rank = 1
            for i in top_bm25_indices:
                if bm25_scores[i] <= 0:
                    break
                doc_id = self._bm25_ids[i]
                meta = self._bm25_metas[i]
                if self._check_where_filter(meta, policy_id, department, active_only, allowed_departments):
                    bm25_ranks[doc_id] = {
                        "rank": rank,
                        "score": bm25_scores[i],
                        "text": self._bm25_docs[i],
                        "meta": meta
                    }
                    rank += 1
                    if len(bm25_ranks) >= n_results:
                        break

        # Reciprocal Rank Fusion (RRF)
        K = 60
        combined_scores = {}
        all_ids = set(semantic_ranks.keys()).union(set(bm25_ranks.keys()))
        
        for doc_id in all_ids:
            rrf_score = 0.0
            sem_data = semantic_ranks.get(doc_id)
            bm25_data = bm25_ranks.get(doc_id)
            
            if sem_data:
                rrf_score += 1.0 / (K + sem_data["rank"])
            if bm25_data:
                rrf_score += 1.0 / (K + bm25_data["rank"])
                
            combined_scores[doc_id] = rrf_score
            
            # Keep metadata from whichever found it
            source_data = sem_data or bm25_data
            hits.append({
                "id": doc_id,
                "text": source_data["text"],
                "score": rrf_score,
                "policy_id": source_data["meta"].get("policy_id", ""),
                "policy_name": source_data["meta"].get("policy_name", ""),
                "version": source_data["meta"].get("version", ""),
                "department": source_data["meta"].get("department", ""),
                "section": source_data["meta"].get("section", ""),
                "page": source_data["meta"].get("page", ""),
                "chunk_index": source_data["meta"].get("chunk_index", ""),
            })

        hits.sort(key=lambda h: h["score"], reverse=True)
        return hits[:top_k]

    def _check_where_filter(self, meta, policy_id, department, active_only, allowed_departments):
        if policy_id is not None and meta.get("policy_id") != str(policy_id): return False
        if department and meta.get("department") != department: return False
        if active_only and meta.get("is_active") != "True": return False
        if allowed_departments:
            if meta.get("department") not in allowed_departments: return False
        return True

    def _build_where(self, policy_id, department, active_only, allowed_departments):
        conditions = []
        if policy_id is not None:
            conditions.append({"policy_id": {"$eq": str(policy_id)}})
        if department:
            conditions.append({"department": {"$eq": department}})
        if active_only:
            conditions.append({"is_active": {"$eq": "True"}})
        if allowed_departments:
            # Previously this only handled the single-department case, so the
            # normal employee case (own department + company-wide "") was
            # silently skipped and NO department filter was applied at all —
            # meaning role-based filtering wasn't actually restricting anything.
            if len(allowed_departments) == 1:
                conditions.append({"department": {"$eq": allowed_departments[0]}})
            else:
                conditions.append({"department": {"$in": allowed_departments}})
        if not conditions:
            return None
        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}

    def count(self) -> int:
        return self._col.count()

    def stats(self) -> dict:
        total = self._col.count()
        return {
            "total_chunks": total,
            "collection": "policy_chunks",
            "path": CHROMA_PATH,
            "model": "chromadb",
        }


# Singleton
_store: Optional[VectorStore] = None

def get_store() -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore()
    return _store
