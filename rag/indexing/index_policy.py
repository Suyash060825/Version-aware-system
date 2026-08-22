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
    from rag.vectordb.chroma import get_store
    store = get_store()
    store.delete_policy(policy_id)
    try:
        from models import db, PolicyChunkV2
        PolicyChunkV2.query.filter_by(policy_id=policy_id).delete()
        db.session.commit()
    except Exception:
        pass
