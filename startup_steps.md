# System Startup & Deployment Guide

This guide outlines the exact, step-by-step instructions to initialize and run the **Version-Aware Enterprise Knowledge Compiler** in both **Development** and **Production** environments.

---

## 🛠️ Option A: Development Environment (Local / Dev Docker)

Use this setup for local development, code changes, and running integration tests.

### Step 1: Verify Environment Variables
Ensure the local `.env` file is present and configured:
```bash
# Verify the .env file contents
cat .env
```

### Step 2: Spin Up Dev Containers
Launch the core services (Flask Web App, Celery Worker, Redis, and Ollama):
```bash
docker compose up -d --build
```

### Step 3: Pull LLM Weights inside Ollama
Since Ollama containers initialize without models, download the Qwen3 model to the dev Ollama container:
```bash
docker exec -it policy_ledger_ollama_dev ollama pull qwen3:4b-q4_K_M
```

### Step 4: Initialize the Database (First-time setup)
Reset and seed the sqlite database schema with initial user roles and test policies:
```bash
docker exec -it policy_ledger_app python seed.py
```

### Step 5: Verify the Setup
Your web application will be accessible at:
👉 **`http://localhost:5000`**

---

## 🌐 Option B: Production Environment (Production Docker Stack)

Use this setup for production deployment. This features a PostgreSQL database, an Nginx reverse proxy, and resource limit restrictions.

### Step 1: Configure Production Secrets
Ensure you modify the production environment variables (e.g., strong passwords, production domain configs) inside your deployment pipeline or custom `.env` file:
```ini
FLASK_ENV=production
SECRET_KEY=your-production-secret-key
POSTGRES_PASSWORD=your-postgres-strong-password
```

### Step 2: Spin Up Production Services
Launch the production containers using the production configuration file:
```bash
docker compose -f docker-compose.prod.yml up -d --build
```

### Step 3: Pull LLM Weights inside Ollama
Download the model weights into the production Ollama container:
```bash
docker exec -it policy_ledger_ollama_prod ollama pull qwen3:4b-q4_K_M
```

### Step 4: Initialize & Run Database Migrations
Initialize your database schemas inside PostgreSQL:
```bash
docker exec -it policy_ledger_web python seed.py
```

### Step 5: Verify Production Proxy
Nginx binds to ports `80` and `443` to route requests to Gunicorn. Access your production dashboard at:
👉 **`http://<your-server-ip-or-domain>`**

---

## 🔍 Telemetry & Verification Commands
- **Check service logs**: `docker compose logs -f`
- **Check background worker status**: `docker exec -it policy_ledger_app celery -A tasks.celery_app status`
- **Verify GPUs are active in container**: `docker exec -it policy_ledger_ollama_dev nvidia-smi`
