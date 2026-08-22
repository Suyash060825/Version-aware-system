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
        import logging
        logger = logging.getLogger("celery.tasks")
        
        result = index_policy_version(policy_id, version_id)
        if not result.get("success"):
            error_msg = result.get("error", "Unknown indexing failure")
            logger.error(f"[Celery] index_policy_version_task failed for policy {policy_id} "
                         f"version {version_id}: {error_msg}")
            # Only retry on transient errors, not on "policy not found" etc.
            transient_errors = ["connection", "timeout", "unavailable"]
            if any(t in error_msg.lower() for t in transient_errors):
                raise self.retry(exc=RuntimeError(error_msg))
            else:
                # Non-retryable: fail immediately with a clear message
                raise RuntimeError(f"Non-retryable indexing failure: {error_msg}")
        return result

@celery_app.task(name="tasks.self_healing_task", bind=True, max_retries=2, default_retry_delay=10)
def self_healing_task(self, msg_id: int):
    """
    Asynchronous Celery task for self-healing a bad response.
    """
    from rag.chatbot.self_healing import trigger_self_healing
    try:
        trigger_self_healing(msg_id)
        return {"success": True}
    except Exception as e:
        import logging
        logging.getLogger("celery.tasks").error(f"[Celery] self_healing_task failed: {e}")
        raise self.retry(exc=e)
