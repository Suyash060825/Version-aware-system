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
    Comprehensively removes all indexed records for a policy across:
    1. Vector store (ChromaDB)
    2. BM25 Sparse Index
    3. Canonical QA Index
    4. Database artifacts (chunks, facts, questions, compiled answers)
    5. Multi-tier caches (semantic cache, evidence filter cache, fact cache, diff cache)
    """
    import logging
    logger = logging.getLogger("rag.indexing")

    # 1. Chroma vector store
    try:
        from rag.vectordb.chroma import get_store
        store = get_store()
        store.delete_policy(policy_id)
    except Exception as e:
        logger.error(f"Failed deleting policy {policy_id} from Chroma: {e}")

    # 2. Database artifacts
    try:
        from models import db, PolicyChunkV2, PolicyFact, CanonicalQuestion, CompiledAnswer
        PolicyChunkV2.query.filter_by(policy_id=policy_id).delete(synchronize_session=False)
        PolicyFact.query.filter_by(policy_id=policy_id).delete(synchronize_session=False)
        q_ids = [q.id for q in CanonicalQuestion.query.filter_by(policy_id=policy_id).all()]
        if q_ids:
            CompiledAnswer.query.filter(CompiledAnswer.question_id.in_(q_ids)).delete(synchronize_session=False)
            CanonicalQuestion.query.filter_by(policy_id=policy_id).delete(synchronize_session=False)
        db.session.commit()
    except Exception as e:
        logger.error(f"Failed deleting policy {policy_id} database artifacts: {e}")

    # 3. BM25 Sparse Index
    try:
        from rag.retrieval.sparse import PersistentBM25Index
        PersistentBM25Index().delete_policy(policy_id)
    except Exception as e:
        logger.error(f"Failed deleting policy {policy_id} from BM25 index: {e}")

    # 4. Canonical QA Index
    try:
        from rag.qa.qa_index import CanonicalQAIndex
        CanonicalQAIndex().delete_policy(policy_id)
    except Exception as e:
        logger.error(f"Failed deleting policy {policy_id} from QA index: {e}")

    # 5. Caches & Invalidation
    try:
        from rag.cache.semantic_cache import get_cache
        get_cache().invalidate_policy(policy_id)
    except Exception:
        pass
    try:
        from rag.authorization.evidence_filter import get_evidence_filter
        get_evidence_filter().clear_cache()
    except Exception:
        pass
    try:
        from rag.facts.fact_resolver import FactResolver
        FactResolver().invalidate()
    except Exception:
        pass
    try:
        from rag.versions.diff_engine import clear_diff_cache
        clear_diff_cache()
    except Exception:
        pass
