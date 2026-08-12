# Production Deployment Checklist

## 1. Environment Separation
- [ ] Ensure `FLASK_ENV=production` is set in all non-dev environments.
- [ ] Use separate `.env` files for Staging and Production.
- [ ] Restrict access to Staging (e.g., VPN or IP whitelist).

## 2. Infrastructure Security
- [ ] **Docker Hardening:**
  - Non-root users (`appuser`) configured in Dockerfile.
  - Root filesystem mounted as `read_only: true`.
  - `tmpfs` mounts used for `/tmp` and `/app/data/uploads`.
  - Resource limits (RAM/CPU) applied to containers.
- [ ] **Network Ports:** Only Nginx exposes ports (80/443). Internal services (Postgres, Redis, Chroma, Ollama, vLLM) are inaccessible from the outside.

## 3. Database & State Backup
- [ ] Automated Cron setup for `scripts/backup.sh` to run nightly.
- [ ] AWS IAM role configured for S3 upload script.
- [ ] S3 Bucket versioning and lifecycle policies (e.g., delete after 90 days) enabled.
- [ ] Periodic restoration drills scheduled (quarterly).

## 4. CI/CD Merge Gates
- [ ] Ensure `pytest` passes on all PRs.
- [ ] Ensure `python eval/run_eval.py` meets the >90% accuracy and >0.90 groundedness thresholds before merge.
- [ ] Code scanning (e.g., SonarQube, Bandit) enabled in CI pipeline.

## 5. Model Weights & API Keys
- [ ] Verify `VLLM_API_KEY` and `SECRET_KEY` are securely injected via secret manager (AWS Secrets Manager / Vault) rather than hardcoded `.env`.
- [ ] Ensure local model weights (`llama3.1`) are pulled to the persistent volume before startup.

## 6. Observability
- [ ] Prometheus scraping metrics endpoint (`/metrics`) enabled.
- [ ] Alerting rules set for High Latency, High Circuit Breaker Open Rate, and Cache Hit Rate drop.
