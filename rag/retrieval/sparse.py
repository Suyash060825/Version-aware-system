import pickle
import os
import logging
from typing import List, Tuple, Dict
from rank_bm25 import BM25Okapi
from models import PolicyChunkV2

logger = logging.getLogger(__name__)

class PersistentBM25Index:
    """
    BM25 index persisted to disk to avoid rebuilding on every cold start
    or having out-of-sync multi-worker instances.
    """
    INDEX_PATH = "data/bm25_index.pkl"
    
    def __init__(self):
        self._bm25 = None
        self._corpus: List[Dict] = []
        self._revision = 0
        self.load()

    def load(self):
        if os.path.exists(self.INDEX_PATH):
            try:
                with open(self.INDEX_PATH, 'rb') as f:
                    data = pickle.load(f)
                    self._bm25 = data['bm25']
                    self._corpus = data['corpus']
                    self._revision = data['revision']
                logger.info(f"Loaded persistent BM25 index (revision {self._revision})")
            except Exception as e:
                logger.error(f"Failed to load BM25 index: {e}")
                self.rebuild_from_db()
        else:
            self.rebuild_from_db()

    def rebuild_from_db(self):
        try:
            # Requires app context
            chunks = PolicyChunkV2.query.all()
            if not chunks:
                return
                
            corpus = []
            tokenized_corpus = []
            for chunk in chunks:
                # Basic tokenization
                tokens = chunk.text.lower().split()
                tokenized_corpus.append(tokens)
                corpus.append({
                    "id": chunk.chunk_id,
                    "text": chunk.text,
                    "policy_id": chunk.policy_id,
                    "version_id": chunk.version_id,
                    "section_path": chunk.section_path
                })
                
            self._bm25 = BM25Okapi(tokenized_corpus)
            self._corpus = corpus
            self._revision += 1
            
            # Save to disk
            os.makedirs(os.path.dirname(self.INDEX_PATH), exist_ok=True)
            with open(self.INDEX_PATH, 'wb') as f:
                pickle.dump({
                    'bm25': self._bm25,
                    'corpus': self._corpus,
                    'revision': self._revision
                }, f)
            logger.info(f"Rebuilt BM25 index with {len(corpus)} chunks")
        except Exception as e:
            logger.error(f"Failed to rebuild BM25 from DB: {e}")

    def get_scores(self, query: str, filters: dict = None) -> List[Tuple[str, float, dict]]:
        if not self._bm25 or not self._corpus:
            return []
            
        tokenized_query = query.lower().split()
        doc_scores = self._bm25.get_scores(tokenized_query)
        
        results = []
        for i, score in enumerate(doc_scores):
            if score > 0:
                doc = self._corpus[i]
                
                # Apply metadata filters
                if filters:
                    match = True
                    for k, v in filters.items():
                        if str(doc.get(k)) != str(v):
                            match = False
                            break
                    if not match:
                        continue
                        
                results.append((doc["id"], float(score), doc))
                
        # Sort by score desc
        return sorted(results, key=lambda x: x[1], reverse=True)
        
    @property
    def revision(self) -> int:
        return self._revision
