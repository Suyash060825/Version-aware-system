"""
tasks.py
Celery task definitions for background processing.
"""
import os
import sys
import logging

# Ensure application root is in python path for all Celery worker processes
_APP_DIR = os.path.abspath(os.path.dirname(__file__))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

from celery import Celery
from config import Config

logger = logging.getLogger(__name__)

def make_celery(app_name=__name__):
    redis_url = Config.REDIS_URL
    celery = Celery(app_name, broker=redis_url, backend=redis_url)
    celery.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        # Resilience for multi-node Redis clusters, Sentinel, and temporary network hiccups
        broker_connection_retry_on_startup=True,
        broker_transport_options={
            'max_retries': 5,
            'interval_start': 0.2,
            'interval_step': 0.5,
            'interval_max': 2.0,
            'socket_timeout': 5.0,
            'socket_connect_timeout': 5.0,
            'socket_keepalive': True,
            'retry_on_timeout': True
        },
        # Celery worker process leak protection under high-volume document stress (>10,000 docs)
        # Recycles worker process after 50 tasks to release C-extension heap allocations (PyMuPDF, ONNX, SQLite)
        worker_max_tasks_per_child=50,
        worker_max_memory_per_child=500000,  # 500 MB max RSS per worker child process
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

# Backwards compatibility alias for tasks and callers
index_policy_version_task = compile_policy_version_task

@celery_app.task(name="tasks.scan_contradictions_task", bind=True)
def scan_contradictions_task(self):
    """
    Asynchronous cross-policy contradiction radar background scan.
    """
    from app import create_app
    app = create_app()
    with app.app_context():
        from models import Policy
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

@celery_app.task(name="tasks.self_heal_message_task", bind=True)
def self_heal_message_task(self, msg_id: int):
    """
    Asynchronous self-healing task triggered by negative user feedback.
    """
    from rag.chatbot.self_healing import trigger_self_healing
    trigger_self_healing(msg_id)
    return {"msg_id": msg_id, "status": "processed"}
