with open('policy-ledger-v2/tasks.py', 'r') as f:
    content = f.read()

repl = """    with app.app_context():
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
        return result"""

import re
content = re.sub(r'    with app\.app_context\(\):\n.*raise self\.retry\(exc=RuntimeError\(error_msg\)\)\n        return result', repl, content, flags=re.DOTALL)

with open('policy-ledger-v2/tasks.py', 'w') as f:
    f.write(content)

