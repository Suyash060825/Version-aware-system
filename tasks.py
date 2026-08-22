"""
tasks.py
Celery task definitions for background processing.
"""
import os
import logging
from celery import Celery

logger = logging.getLogger(__name__)

def make_celery(app_name=__name__):
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    celery = Celery(app_name, broker=redis_url, backend=redis_url)
    celery.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
    )
    return celery

celery_app = make_celery()

@celery_app.task(name="tasks.compile_policy_version_task", bind=True, max_retries=3)
def compile_policy_version_task(self, policy_id: int, version_id: int):
    """
    Full knowledge compilation pipeline as Celery task.
    Replaces simple index_policy_version_task for new architecture.
    """
    from app import create_app
    app = create_app()
    with app.app_context():
        from rag.compiler.pipeline import KnowledgeCompilerPipeline
        from models import CompilationStage
        pipeline = KnowledgeCompilerPipeline()
        job = pipeline.compile(policy_id, version_id)
        if job.stage == CompilationStage.FAILED:
            raise self.retry(exc=RuntimeError(job.error))
        return {"stage": job.stage, "chunks": job.chunk_count, "facts": job.fact_count}
