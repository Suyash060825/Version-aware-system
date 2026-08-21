"""
tasks.py
Celery background worker configuration and tasks for async document indexing.
Run worker: celery -A tasks.celery_app worker --loglevel=info
"""
import os
from celery import Celery

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "policy_ledger_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 min hard limit per indexing job
)


@celery_app.task(name="tasks.index_policy_version_task", bind=True, max_retries=3, default_retry_delay=10)
def index_policy_version_task(self, policy_id: int, version_id: int):
    """
    Asynchronous Celery task for policy indexing.
    Offloads heavy sentence-transformer embedding & ChromaDB upserts off Flask request threads.
    """
    from app import create_app
    env = os.environ.get("FLASK_ENV") or os.environ.get("APP_ENV", "production")
    app = create_app(env)
    
    with app.app_context():
        from rag.indexing.index_policy import index_policy_version
        result = index_policy_version(policy_id, version_id)
        if not result.get("success"):
            error_msg = result.get("error", "Unknown indexing failure")
            # Retry on transient failures
            raise self.retry(exc=RuntimeError(error_msg))
        return result
