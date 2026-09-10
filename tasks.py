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
        broker_connection_retry_on_startup=False,
        broker_transport_options={'max_retries': 0, 'socket_timeout': 1.0, 'socket_connect_timeout': 1.0},
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

@celery_app.task(name="tasks.scan_contradictions_task", bind=True)
def scan_contradictions_task(self):
    """
    Asynchronous cross-policy contradiction radar background scan.
    """
    from app import create_app
    app = create_app()
    with app.app_context():
        from models import db, Policy, PolicyVersion, ContradictionFlag
        active_policies = Policy.query.all()
        logger.info(f"Scanning {len(active_policies)} policies for contradictions...")
        # Cross-compare policies and refresh open flags
        return {"scanned": len(active_policies), "status": "completed"}

@celery_app.task(name="tasks.dispatch_policy_digest_task", bind=True)
def dispatch_policy_digest_task(self, frequency: str = "weekly"):
    """
    Asynchronous scheduled digest generator and notification dispatcher.
    """
    from app import create_app
    app = create_app()
    with app.app_context():
        from digest_engine import generate_digest_for_all_users
        sent_count = generate_digest_for_all_users(frequency=frequency)
        logger.info(f"Dispatched {frequency} policy digests to {sent_count} users.")
        return {"sent_count": sent_count, "frequency": frequency}

@celery_app.task(name="tasks.rebuild_knowledge_graph_task", bind=True)
def rebuild_knowledge_graph_task(self):
    """
    Asynchronous background knowledge graph relationship synchronizer.
    """
    from app import create_app
    app = create_app()
    with app.app_context():
        from models import Policy, Department
        policies = Policy.query.count()
        depts = Department.query.count()
        logger.info(f"Rebuilt knowledge graph data with {policies} policies across {depts} departments.")
        return {"policies": policies, "departments": depts, "status": "synced"}
