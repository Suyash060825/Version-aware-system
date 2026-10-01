"""
rag/indexing/index_policy.py
Indexes a policy version into the vector store.
Called after HR uploads/publishes a policy.
"""
from datetime import datetime

def index_policy_version(policy_id: int, version_id: int, app=None) -> dict:
    result = {"success": False, "chunks": 0, "error": None}
    try:
        if app:
            ctx = app.app_context()
            ctx.push()

        from rag.compiler.pipeline import KnowledgeCompilerPipeline
        pipeline = KnowledgeCompilerPipeline()
        job = pipeline.compile(policy_id, version_id)
        
        from models import CompilationStage
        if job.stage == CompilationStage.FAILED:
            result["error"] = job.error
            return result
            
        result["success"] = True
        result["chunks"] = job.chunk_count

    except Exception as e:
        result["error"] = str(e)
    return result

def delete_policy_from_index(policy_id: int):
    """
    Completely purge a policy from all search indexes (Chroma, BM25, FAISS QA index),
    cache, and database compilation tables.
    """
    try:
        from rag.vectordb.chroma import get_store
        get_store().delete_policy(policy_id)
    except Exception:
        pass

    try:
        from rag.retrieval.sparse import PersistentBM25Index
        PersistentBM25Index().delete_policy(policy_id)
    except Exception:
        pass

    try:
        from rag.qa.qa_index import CanonicalQAIndex
        CanonicalQAIndex().delete_policy(policy_id)
    except Exception:
        pass

    try:
        from rag.cache.semantic_cache import get_cache
        cache = get_cache()
        # Invalidate any cache entries mentioning this policy
        if hasattr(cache, "clear"):
            cache.clear()
    except Exception:
        pass

    try:
        from models import db, PolicyChunkV2, PolicyFact, CanonicalQuestion, CompiledAnswer, CompilationJob
        q_ids = [q.id for q in CanonicalQuestion.query.filter_by(policy_id=policy_id).all()]
        if q_ids:
            CompiledAnswer.query.filter(CompiledAnswer.question_id.in_(q_ids)).delete(synchronize_session=False)
            CanonicalQuestion.query.filter_by(policy_id=policy_id).delete(synchronize_session=False)
        PolicyChunkV2.query.filter_by(policy_id=policy_id).delete(synchronize_session=False)
        PolicyFact.query.filter_by(policy_id=policy_id).delete(synchronize_session=False)
        CompilationJob.query.filter_by(policy_id=policy_id).delete(synchronize_session=False)
        db.session.commit()
    except Exception:
        pass
