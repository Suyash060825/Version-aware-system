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
        self._sub_bm25 = None
        self._sub_bm25_cache_key = None
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

    @property
    def corpus(self):
        return self._corpus

    @corpus.setter
    def corpus(self, val):
        self._corpus = val

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
        from flask import has_app_context
        if not has_app_context():
            try:
                from app import create_app
                app = create_app("default")
                with app.app_context():
                    return self._do_rebuild_from_db()
            except Exception as e:
                logger.warning(f"rebuild_from_db invoked outside Flask context and auto-context creation failed: {e}")
                return
        return self._do_rebuild_from_db()

    def _do_rebuild_from_db(self):
        try:
            chunks = PolicyChunkV2.query.all()
            if not chunks:
                self._corpus = []
                self._tokenized_corpus = []
                self._bm25 = None
                return
                
            from models import Policy, PolicyVersion
            from datetime import datetime, time
            versions_map = {v.id: v for v in PolicyVersion.query.all()}
            policies_map = {p.id: p for p in Policy.query.all()}

            corpus = []
            tokenized_corpus = []
            for chunk in chunks:
                pv = versions_map.get(chunk.version_id)
                pol = policies_map.get(chunk.policy_id)
                v_num = float(pv.version_num) if pv and pv.version_num is not None else 1.0
                v_lbl = pv.version_label if pv and pv.version_label else f"v{v_num}"
                is_curr = bool(pv.is_active) if pv else True
                p_name = pol.title if pol else "Policy"

                valid_from_ts = 0
                valid_to_ts = 32472144000
                if pv and pv.effective_from:
                    valid_from_ts = int(datetime.combine(pv.effective_from, time.min).timestamp())
                if pv and pv.effective_to:
                    valid_to_ts = int(datetime.combine(pv.effective_to, time.max).timestamp())

                contextual_text = f"[{p_name} {v_lbl} {chunk.section_path or 'General'}] {chunk.text}"
                tokens = re.findall(r"\b\w+\b", contextual_text.lower())
                tokenized_corpus.append(tokens)
                corpus.append({
                    "id": chunk.chunk_id,
                    "chunk_id": chunk.chunk_id,
                    "text": chunk.text,
                    "policy_id": chunk.policy_id,
                    "policy_name": p_name,
                    "version_id": chunk.version_id,
                    "version": v_lbl,
                    "version_num": v_num,
                    "is_current": is_curr,
                    "valid_from_ts": valid_from_ts,
                    "valid_to_ts": valid_to_ts,
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
            p_name = chunk.get("policy_name", "Policy")
            v_lbl = str(chunk.get("version", version_id))
            section = chunk.get("section") or chunk.get("section_path") or "General"
            contextual_text = f"[{p_name} {v_lbl} {section}] {text}"

            filtered_corpus.append({
                "id": chunk.get("chunk_id") or chunk.get("id"),
                "chunk_id": chunk.get("chunk_id") or chunk.get("id"),
                "text": text,
                "policy_id": policy_id,
                "policy_name": p_name,
                "version_id": version_id,
                "version": v_lbl,
                "version_num": chunk.get("version_num", 1.0),
                "is_current": chunk.get("is_current", True),
                "valid_from_ts": chunk.get("valid_from_ts", 0),
                "valid_to_ts": chunk.get("valid_to_ts", 32472144000),
                "section": section,
                "section_path": chunk.get("section_path") or section,
                "page": chunk.get("page", 1)
            })
            filtered_tokens.append(re.findall(r"\b\w+\b", contextual_text.lower()))

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

    def delete_policy(self, policy_id: int):
        """Incremental deletion for an entire policy without re-tokenizing unchanged corpus."""
        p_val = int(policy_id) if str(policy_id).isdigit() else policy_id
        kept_indices = [
            i for i, c in enumerate(self._corpus)
            if c.get("policy_id") != p_val and str(c.get("policy_id")) != str(p_val)
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
        logger.info(f"Deleted policy {policy_id} from BM25 index (revision {self._revision})")

    def _matches_filters(self, doc: dict, filters: dict) -> bool:
        for k, v in filters.items():
            if k in ("is_active", "is_current"):
                doc_val = doc.get("is_active")
                if doc_val is None:
                    doc_val = doc.get("is_current", True)
                if bool(doc_val) != bool(v):
                    return False
                continue
            doc_val = doc.get(k)
            if isinstance(v, dict):
                for op, op_val in v.items():
                    if op == "$lte" and not (doc_val is not None and doc_val <= op_val):
                        return False
                    elif op == "$gte" and not (doc_val is not None and doc_val >= op_val):
                        return False
                    elif op == "$lt" and not (doc_val is not None and doc_val < op_val):
                        return False
                    elif op == "$gt" and not (doc_val is not None and doc_val > op_val):
                        return False
                    elif op == "$in" and not (doc_val in op_val or str(doc_val) in [str(x) for x in op_val]):
                        return False
                    elif op == "$eq" and not (doc_val == op_val or str(doc_val) == str(op_val)):
                        return False
            elif isinstance(v, (list, tuple, set)):
                if doc_val not in v and str(doc_val) not in [str(x) for x in v]:
                    return False
            elif str(doc_val) != str(v):
                return False
        return True

    def get_scores(self, query: str, filters: dict = None, scope: Any = None) -> List[Tuple[str, float, dict]]:
        if not self._bm25 or not self._corpus:
            self.load()
        if not self._bm25 or not self._corpus:
            return []
            
        tokenized_query = re.findall(r"\b\w+\b", query.lower())
        if not tokenized_query:
            return []

        # Build allowed indices set BEFORE scoring (pre-filter for O(k) not O(N))
        allowed_indices = []
        for i, doc in enumerate(self._corpus):
            if scope:
                if getattr(scope, "allowed_policy_ids", None) is not None:
                    if doc.get("policy_id") not in scope.allowed_policy_ids:
                        continue
                if getattr(scope, "allowed_version_ids", None) is not None:
                    if doc.get("version_id") not in scope.allowed_version_ids:
                        continue
            if filters and not self._matches_filters(doc, filters):
                continue
            allowed_indices.append(i)

        if not allowed_indices:
            return []

        # Guard: only use subset scoring if len(self._corpus) > 2000 and len(allowed_indices) < len(self._corpus)
        if len(self._corpus) > 2000 and len(allowed_indices) < len(self._corpus) and self._tokenized_corpus:
            cache_key = (frozenset(allowed_indices), self._revision)
            if cache_key != self._sub_bm25_cache_key or self._sub_bm25 is None:
                allowed_tokenized = [self._tokenized_corpus[i] for i in allowed_indices]
                self._sub_bm25 = BM25Okapi(allowed_tokenized)
                self._sub_bm25_cache_key = cache_key
            scores = self._sub_bm25.get_scores(tokenized_query)
            results = []
            for j, score in enumerate(scores):
                if score > 0:
                    doc = self._corpus[allowed_indices[j]]
                    results.append((doc["id"], float(score), doc))
            return sorted(results, key=lambda x: x[1], reverse=True)

        doc_scores = self._bm25.get_scores(tokenized_query)
        results = []
        for i in allowed_indices:
            score = doc_scores[i]
            if score > 0:
                doc = self._corpus[i]
                results.append((doc["id"], float(score), doc))
        return sorted(results, key=lambda x: x[1], reverse=True)
        
    @property
    def revision(self) -> int:
        return self._revision
