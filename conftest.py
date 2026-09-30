import os
import tempfile
import atexit
import shutil
import pytest

os.environ["EMBEDDING_DEVICE"] = "cpu"
os.environ["RERANKER_DEVICE"] = "cpu"
os.environ["ENTAILMENT_ENABLED"] = "true"

# GLOBAL ISOLATION for setUpClass / module-level code
global_test_dir = tempfile.mkdtemp(prefix="veritas_global_")
def cleanup_global():
    shutil.rmtree(global_test_dir, ignore_errors=True)
atexit.register(cleanup_global)

# Copy production db to isolated temp db so tests have seeded schema/users
import shutil
test_db_path = os.path.join(global_test_dir, 'test_ledger.db')
prod_db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data', 'ledger.db')
if os.path.exists(prod_db_path):
    shutil.copy2(prod_db_path, test_db_path)

os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path}"

import rag.retrieval.sparse
rag.retrieval.sparse.PersistentBM25Index.INDEX_PATH = os.path.join(global_test_dir, "bm25_index.pkl")

import rag.qa.qa_index
rag.qa.qa_index.CanonicalQAIndex.INDEX_FILE = os.path.join(global_test_dir, "canonical_qa_faiss.index")
rag.qa.qa_index.CanonicalQAIndex.META_FILE = os.path.join(global_test_dir, "canonical_qa_faiss.meta.pkl")
rag.qa.qa_index.CanonicalQAIndex.DELTA_INDEX_FILE = os.path.join(global_test_dir, "canonical_qa_faiss_delta.index")

import rag.vectordb.chroma as chroma_module
chroma_module.CHROMA_PATH = os.path.join(global_test_dir, "chroma")
chroma_module._store = None

global_original_init = chroma_module.VectorStore.__init__
def global_new_init(self, path=None):
    if path is None or path == "data/chroma":
        path = os.path.join(global_test_dir, "chroma")
    global_original_init(self, path=path)
chroma_module.VectorStore.__init__ = global_new_init


# PER-TEST ISOLATION to prevent test interference
@pytest.fixture(autouse=True)
def isolate_test_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/15")
    
    monkeypatch.setattr(rag.retrieval.sparse.PersistentBM25Index, "INDEX_PATH", str(tmp_path / "bm25_index.pkl"))
    
    monkeypatch.setattr(rag.qa.qa_index.CanonicalQAIndex, "INDEX_FILE", str(tmp_path / "canonical_qa_faiss.index"))
    monkeypatch.setattr(rag.qa.qa_index.CanonicalQAIndex, "META_FILE", str(tmp_path / "canonical_qa_faiss.meta.pkl"))
    monkeypatch.setattr(rag.qa.qa_index.CanonicalQAIndex, "DELTA_INDEX_FILE", str(tmp_path / "canonical_qa_faiss_delta.index"))

    chroma_path = str(tmp_path / "chroma")
    monkeypatch.setattr(chroma_module, "CHROMA_PATH", chroma_path)
    monkeypatch.setattr(chroma_module, "_store", None)
    
    def test_new_init(self, path=None):
        if path is None or path == "data/chroma" or path == os.path.join(global_test_dir, "chroma"):
            path = chroma_path
        global_original_init(self, path=path)
    monkeypatch.setattr(chroma_module.VectorStore, "__init__", test_new_init)
