"""
rag/retrieval/sparse.py
Persistent BM25 sparse keyword retriever with incremental delta updates, partition filtering, and revision tracking.
"""
import pickle
import os
import re
import logging
from typing import List, Tuple, Dict, Any, Optional
from rank_bm25 import BM25Okapi
from models import PolicyChunkV2

logger = logging.getLogger("rag.retrieval.sparse")

class PersistentBM25Index:
    INDEX_PATH = "data/bm25_index.pkl"
    
    def __init__(self):
        self._bm25 = None
        self._corpus: List[Dict[str, Any]] = []
        self._tokenized_corpus: List[List[str]] = []
        self._revision = 0
        self.load()

    def load(self):
        if os.path.exists(self.INDEX_PATH):
            try:
                with open(self.INDEX_PATH, 'rb') as f:
                    data = pickle.load(f)
                    self._bm25 = data['bm25']
                    self._corpus = data['corpus']
                    self._tokenized_corpus = data.get('tokenized_corpus')
                    if self._tokenized_corpus is None or len(self._tokenized_corpus) != len(self._corpus):
                        self._tokenized_corpus = [re.findall(r"\b\w+\b", c["text"].lower()) for c in self._corpus]
                    self._revision = data.get('revision', 0)
                logger.info(f"Loaded persistent BM25 index with {len(self._corpus)} documents (revision {self._revision})")
                return
            except Exception as e:
                logger.error(f"Failed to load BM25 index from {self.INDEX_PATH}: {e}. Rebuilding...")
        self.rebuild_from_db()

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.INDEX_PATH), exist_ok=True)
            tmp_path = self.INDEX_PATH + ".tmp"
            with open(tmp_path, 'wb') as f:
                pickle.dump({
                    'bm25': self._bm25,
                    'corpus': self._corpus,
                    'tokenized_corpus': self._tokenized_corpus,
                    'revision': self._revision
                }, f)
            os.replace(tmp_path, self.INDEX_PATH)
        except Exception as e:
            logger.error(f"Failed to save BM25 index: {e}")

    def rebuild_from_db(self):
        try:
            chunks = PolicyChunkV2.query.all()
            if not chunks:
                self._corpus = []
                self._tokenized_corpus = []
                self._bm25 = None
                return
                
            corpus = []
            tokenized_corpus = []
            for chunk in chunks:
                tokens = re.findall(r"\b\w+\b", chunk.text.lower())
                tokenized_corpus.append(tokens)
                corpus.append({
                    "id": chunk.chunk_id,
                    "chunk_id": chunk.chunk_id,
                    "text": chunk.text,
                    "policy_id": chunk.policy_id,
                    "version_id": chunk.version_id,
                    "version": str(chunk.version_id),
                    "section": chunk.section_path or "General",
                    "section_path": chunk.section_path or "General",
                    "page": chunk.page or 1
                })
                
            self._bm25 = BM25Okapi(tokenized_corpus)
            self._corpus = corpus
            self._tokenized_corpus = tokenized_corpus
            self._revision += 1
            self.save()
            logger.info(f"Rebuilt BM25 index with {len(corpus)} chunks (revision {self._revision})")
        except Exception as e:
            logger.error(f"Failed to rebuild BM25 from DB: {e}")

    def update_policy_version(self, policy_id: int, version_id: int, new_chunks: List[Dict[str, Any]]):
        """
        Incremental delta update: replaces/inserts chunks for a single policy version
        without re-tokenizing the entire corpus.
        """
        kept_indices = [
            i for i, c in enumerate(self._corpus)
            if not (c.get("policy_id") == policy_id and c.get("version_id") == version_id)
        ]
        filtered_corpus = [self._corpus[i] for i in kept_indices]
        if self._tokenized_corpus and len(self._tokenized_corpus) == len(self._corpus):
            filtered_tokens = [self._tokenized_corpus[i] for i in kept_indices]
        else:
            filtered_tokens = [re.findall(r"\b\w+\b", c["text"].lower()) for c in filtered_corpus]
        
        # Add and tokenize only the new delta chunks
        for chunk in new_chunks:
            text = chunk.get("text", "")
            filtered_corpus.append({
                "id": chunk.get("chunk_id") or chunk.get("id"),
                "chunk_id": chunk.get("chunk_id") or chunk.get("id"),
                "text": text,
                "policy_id": policy_id,
                "version_id": version_id,
                "version": str(chunk.get("version", version_id)),
                "section": chunk.get("section") or chunk.get("section_path") or "General",
                "section_path": chunk.get("section_path") or chunk.get("section") or "General",
                "page": chunk.get("page", 1)
            })
            filtered_tokens.append(re.findall(r"\b\w+\b", text.lower()))

        self._corpus = filtered_corpus
        self._tokenized_corpus = filtered_tokens
        if self._tokenized_corpus:
            self._bm25 = BM25Okapi(self._tokenized_corpus)
        else:
            self._bm25 = None
        self._revision += 1
        self.save()
        logger.info(f"Incrementally updated BM25 for policy {policy_id} v{version_id} ({len(new_chunks)} chunks, rev {self._revision})")

    def delete_policy_version(self, policy_id: int, version_id: int):
        """Incremental deletion for a policy version without re-tokenizing unchanged corpus."""
        kept_indices = [
            i for i, c in enumerate(self._corpus)
            if not (c.get("policy_id") == policy_id and c.get("version_id") == version_id)
        ]
        self._corpus = [self._corpus[i] for i in kept_indices]
        if self._tokenized_corpus and len(self._tokenized_corpus) >= len(kept_indices):
            self._tokenized_corpus = [self._tokenized_corpus[i] for i in kept_indices if i < len(self._tokenized_corpus)]
        else:
            self._tokenized_corpus = [re.findall(r"\b\w+\b", c["text"].lower()) for c in self._corpus]

        if self._tokenized_corpus:
            self._bm25 = BM25Okapi(self._tokenized_corpus)
        else:
            self._bm25 = None
        self._revision += 1
        self.save()

    def get_scores(self, query: str, filters: dict = None, scope: Any = None) -> List[Tuple[str, float, dict]]:
        if not self._bm25 or not self._corpus:
            self.load()
        if not self._bm25 or not self._corpus:
            return []
            
        tokenized_query = re.findall(r"\b\w+\b", query.lower())
        if not tokenized_query:
            return []
        doc_scores = self._bm25.get_scores(tokenized_query)
        
        results = []
        for i, score in enumerate(doc_scores):
            if score > 0:
                doc = self._corpus[i]
                
                # Scope-based pre-filtering
                if scope:
                    if getattr(scope, "allowed_policy_ids", None) is not None:
                        if doc.get("policy_id") not in scope.allowed_policy_ids:
                            continue
                    if getattr(scope, "allowed_version_ids", None) is not None:
                        if doc.get("version_id") not in scope.allowed_version_ids:
                            continue

                # Pre-filtered partition matching
                if filters:
                    match = True
                    for k, v in filters.items():
                        if isinstance(v, list):
                            if str(doc.get(k)) not in [str(x) for x in v]:
                                match = False
                                break
                        elif str(doc.get(k)) != str(v):
                            match = False
                            break
                    if not match:
                        continue
                        
                results.append((doc["id"], float(score), doc))
                
        return sorted(results, key=lambda x: x[1], reverse=True)
        
    @property
    def revision(self) -> int:
        return self._revision
