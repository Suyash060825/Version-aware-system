import os
import re

with open("scripts/test_policy_creation_lifecycle.py", "r") as f:
    content = f.read()

setup_patch = """
    @classmethod
    def setUpClass(cls):
        import os, tempfile, shutil
        cls.test_dir = tempfile.mkdtemp(prefix="veritas_test_")
        
        import rag.retrieval.sparse
        rag.retrieval.sparse.PersistentBM25Index.INDEX_PATH = os.path.join(cls.test_dir, "bm25_index.pkl")
        
        import rag.qa.qa_index
        rag.qa.qa_index.CanonicalQAIndex.INDEX_FILE = os.path.join(cls.test_dir, "canonical_qa_faiss.index")
        rag.qa.qa_index.CanonicalQAIndex.META_FILE = os.path.join(cls.test_dir, "canonical_qa_faiss.meta.pkl")
        rag.qa.qa_index.CanonicalQAIndex.DELTA_INDEX_FILE = os.path.join(cls.test_dir, "canonical_qa_faiss_delta.index")
        
        import rag.vectordb.chroma as chroma_module
        chroma_module.CHROMA_PATH = os.path.join(cls.test_dir, "chroma")
        chroma_module._store = None
        cls.original_chroma_init = chroma_module.VectorStore.__init__
        def test_new_init(self, path=None):
            if path is None or path == "data/chroma":
                path = chroma_module.CHROMA_PATH
            cls.original_chroma_init(self, path=path)
        chroma_module.VectorStore.__init__ = test_new_init
        
        os.environ["REDIS_URL"] = "redis://localhost:6379/15"

        import sys, traceback
        from rag.compiler.pipeline import KnowledgeCompilerPipeline
        cls.original_advance = KnowledgeCompilerPipeline._advance_stage
        
        def diagnostic_advance(self, job, target_stage, execute_fn):
            print(f"\\n[DIAGNOSTIC] Advancing job {job.id} to {target_stage}. Previous stage: {job.stage}")
            try:
                return cls.original_advance(self, job, target_stage, execute_fn)
            except Exception as e:
                print(f"\\n[DIAGNOSTIC EXCEPTION] in _advance_stage for {target_stage}:")
                traceback.print_exc(file=sys.stdout)
                raise
        KnowledgeCompilerPipeline._advance_stage = diagnostic_advance

"""

content = re.sub(r'    @classmethod\n    def setUpClass\(cls\):', setup_patch, content)

teardown_patch = """
    @classmethod
    def tearDownClass(cls):
        import shutil
        shutil.rmtree(cls.test_dir, ignore_errors=True)
        import rag.vectordb.chroma as chroma_module
        chroma_module.VectorStore.__init__ = cls.original_chroma_init
"""
content = content + teardown_patch

with open("scripts/test_policy_creation_lifecycle.py", "w") as f:
    f.write(content)

