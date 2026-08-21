import yaml

# Read original
with open('policy-ledger-v2/docker-compose.yml', 'r') as f:
    # Use load to not mess up formatting too much, but maybe string replace is safer
    content = f.read()

# Add Celery worker
celery_worker = """
  celery_worker:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: policy_ledger_celery
    command: celery -A tasks.celery_app worker --loglevel=info --concurrency=2
    restart: unless-stopped
    environment:
      - FLASK_ENV=development
      - SECRET_KEY=${SECRET_KEY:-dev-secret-key-change-in-prod}
      - REDIS_URL=redis://:${REDIS_PASSWORD:-devpassword123}@redis:6379/0
      - LLM_BACKEND=${LLM_BACKEND:-lmstudio}
      - LMSTUDIO_BASE_URL=http://host.docker.internal:1234/v1
      - LOCAL_LLM_MODEL=${LOCAL_LLM_MODEL:-local-model}
      - HF_HOME=/app/data/huggingface
    extra_hosts:
      - "host.docker.internal:host-gateway"
    volumes:
      - .:/app:z
      - app_data:/app/data:z
    depends_on:
      redis:
        condition: service_started
      web:
        condition: service_started
"""

content = content.replace("  redis:\n", celery_worker + "\n  redis:\n")

# Modify Redis URL in web
content = content.replace("REDIS_URL=redis://redis:6379/0", "REDIS_URL=redis://:${REDIS_PASSWORD:-devpassword123}@redis:6379/0")

# Modify Redis configuration
redis_orig = """  redis:
    image: redis:7-alpine
    container_name: policy_ledger_redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data"""

redis_new = """  redis:
    image: redis:7-alpine
    container_name: policy_ledger_redis
    restart: unless-stopped
    command: redis-server --requirepass ${REDIS_PASSWORD:-devpassword123} --appendonly yes --appendfsync everysec
    volumes:
      - redis_data:/data"""

content = content.replace(redis_orig, redis_new)

with open('policy-ledger-v2/docker-compose.yml', 'w') as f:
    f.write(content)

