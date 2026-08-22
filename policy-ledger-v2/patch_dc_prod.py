import yaml
import re

with open('policy-ledger-v2/docker-compose.prod.yml', 'r') as f:
    content = f.read()

# Bug 14: Remove version: '3.8'
content = re.sub(r"version:\s*'3.8'\s*\n", "", content)

# Bug 5: Remove tmpfs uploads, separate volume for uploads
content = re.sub(
    r"""    tmpfs:
      - /tmp
      - /app/data/uploads
    volumes:
      - app_data:/app/data""",
    r"""    tmpfs:
      - /tmp
    volumes:
      - app_data:/app/data
      - upload_data:/app/data/uploads""",
    content
)

# Bug 6 & Bug 12 & Bug 13: 
# Web env additions
web_env_orig = """      - VLLM_BASE_URL=http://vllm:8000/v1"""
web_env_new = """      - VLLM_BASE_URL=http://vllm:8000/v1
      - HF_HOME=/app/data/huggingface
      - LMSTUDIO_BASE_URL=http://host.docker.internal:1234/v1"""

content = content.replace(web_env_orig, web_env_new)

# Add extra_hosts to web
extra_hosts_web = """    extra_hosts:
      - "host.docker.internal:host-gateway"
    depends_on:"""
content = content.replace("    depends_on:", extra_hosts_web, 1)

# Celery env additions
celery_env_orig = """      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - REDIS_URL=redis://redis:6379/0"""
celery_env_new = """      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - REDIS_URL=redis://redis:6379/0
      - HF_HOME=/app/data/huggingface
      - LLM_BACKEND=${LLM_BACKEND:-ollama}
      - LOCAL_LLM_MODEL=${LOCAL_LLM_MODEL}
      - LMSTUDIO_BASE_URL=http://host.docker.internal:1234/v1"""

content = content.replace(celery_env_orig, celery_env_new)

# Extra hosts to celery
extra_hosts_celery = """    extra_hosts:
      - "host.docker.internal:host-gateway"
    depends_on:"""
# Let's find celery depends_on
content = re.sub(
    r"""    depends_on:
      - postgres
      - redis""",
    r"""    depends_on:
      postgres:
        condition: service_started
      redis:
        condition: service_started
    extra_hosts:
      - "host.docker.internal:host-gateway" """,
    content
)

# Bug 10: Web healthcheck
web_hc = """    read_only: true
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:5000/rag/health || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 30s"""
content = content.replace("    read_only: true", web_hc, 1)

# Nginx depends_on web condition
nginx_depends = """    depends_on:
      web:
        condition: service_healthy"""
content = re.sub(r"""    depends_on:\s*- web""", nginx_depends, content)

# Bug 9: Redis AOF
redis_orig = """  redis:
    image: redis:7-alpine
    container_name: policy_ledger_redis
    restart: always"""
redis_new = """  redis:
    image: redis:7-alpine
    container_name: policy_ledger_redis
    restart: always
    command: redis-server --appendonly yes --appendfsync everysec"""
content = content.replace(redis_orig, redis_new)

# Add upload_data to volumes
content = content.replace("""  app_data:""", """  app_data:
  upload_data:""")

with open('policy-ledger-v2/docker-compose.prod.yml', 'w') as f:
    f.write(content)

