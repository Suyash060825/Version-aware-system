import re

with open("scripts/test_policy_creation_lifecycle.py", "r") as f:
    content = f.read()

setup_replacement = """
    @classmethod
    def setUpClass(cls):
        import os, tempfile, sys, traceback
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

        import rag.compiler.pipeline
        cls.original_auto = rag.compiler.pipeline.auto_compile_policy_version
        
        def diagnostic_auto(policy_id, version_id):
            try:
                return cls.original_auto(policy_id, version_id)
            except Exception as e:
                print("\\n[DIAGNOSTIC] EXCEPTION IN AUTO_COMPILE:", str(e))
                traceback.print_exc(file=sys.stdout)
                raise e
        rag.compiler.pipeline.auto_compile_policy_version = diagnostic_auto

        cls.original_advance = rag.compiler.pipeline.KnowledgeCompilerPipeline._advance_stage
        
        def diagnostic_advance(self, job, target_stage, execute_fn):
            print(f"\\n[DIAGNOSTIC] Advancing job {job.id} to {target_stage}. Previous stage: {job.stage}")
            try:
                execute_fn(job)
                from models import db
                db.session.commit()
            except Exception as execute_err:
                print(f"\\n[DIAGNOSTIC] EXCEPTION IN EXECUTE_FN ({target_stage}):", str(execute_err))
                traceback.print_exc(file=sys.stdout)
                # IMPORTANT: we must replicate the failure behavior!
                # Wait, if we raise it here, it will be caught by auto_compile!
                # That perfectly logs the exception!
                raise execute_err
            return job
        rag.compiler.pipeline.KnowledgeCompilerPipeline._advance_stage = diagnostic_advance

        cls.app = create_app()
"""

content = content.replace("    @classmethod\n    def setUpClass(cls):\n        cls.app = create_app()", setup_replacement)

teardown_replacement = """
    @classmethod
    def tearDownClass(cls):
        import shutil
        shutil.rmtree(cls.test_dir, ignore_errors=True)
        import rag.vectordb.chroma as chroma_module
        chroma_module.VectorStore.__init__ = cls.original_chroma_init
        import rag.compiler.pipeline
        rag.compiler.pipeline.auto_compile_policy_version = cls.original_auto
        rag.compiler.pipeline.KnowledgeCompilerPipeline._advance_stage = cls.original_advance
"""

content = content + teardown_replacement

with open("scripts/test_policy_creation_lifecycle.py", "w") as f:
    f.write(content)
