# System Startup & Quickstart Guide
**Version-Aware Enterprise Policy Intelligence & Knowledge Compiler System**

This guide provides step-by-step instructions to open, run, reseed, test, and shut down this project in both **Docker (Recommended)** and **Local Native Python** modes.

---

## ⚡ Quick Start: 3-Step Launch (Docker)

If you have Docker running on your machine, this is the quickest way to launch the full stack (Web UI, Celery Workers, Redis, and Ollama LLM):

### Step 1: Start the Containers
```bash
docker compose up -d
```
*(Add `--build` if you made any code or dependency modifications: `docker compose up -d --build`)*

### Step 2: Seed & Compile the 20 Enterprise Policies
To load all 20 corporate policies, 33 structured facts, 100 canonical Q&As, and ChromaDB vector embeddings into the system:
```bash
docker exec -it policy_ledger_app python seed.py
```

### Step 3: Open in Browser
Open your browser and navigate to:
👉 **`http://localhost:5000`**

---

## 🔐 Default Login Credentials

| Role | Email | Password | Access Level |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@company.com` | `admin123` | Full administrative control, all 20 policies, user management, policy version editing |
| **HR Manager** | `hr@company.com` | `hr123` | HR, benefits, leave, performance, and internal policies |
| **Compliance Officer**| `compliance@company.com` | `comp123` | Legal, privacy (DPDP/GDPR), POSH, anti-bribery policies |
| **Employee** | `employee@company.com` | `emp123` | Company-wide internal policies, AI Assistant, What-If Simulator |

---

## 🐍 Option B: Run Locally (Native Python / Virtualenv)

If you prefer running directly in your local terminal without Docker:

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Seed Database & Compile Knowledge Base
```bash
python seed.py
```

### 3. Start Background Redis & Celery (Optional for async compilations)
```bash
# Terminal 1: Celery Worker
celery -A tasks.celery_app worker --loglevel=info --concurrency=2
```

### 4. Start the Web Application
```bash
# Terminal 2: Flask App
python app.py
```
Open **`http://localhost:5000`** in your browser.

---

## 🤖 Pulling Local LLM Weights (Optional for Ollama)

If you want the local LLM generation fallback active inside Ollama:
```bash
docker exec -it policy_ledger_ollama_dev ollama pull qwen3:4b-q4_K_M
```
*(Note: If Ollama is offline or busy, the system automatically uses fast deterministic extraction in <10ms without errors or lag).*

---

## 🧪 Testing Key Features

### 1. AI Assistant Querying
Try asking the AI Assistant factual questions:
* *"What is the base health insurance cover?"* → **Rs. 5,00,000**
* *"What is the annual learning budget for an employee?"* → **Rs. 40,000**
* *"What is the standard notice period for confirmed staff?"* → **2 months**
* *"What is the maximum domestic hotel limit per night?"* → **Rs. 5,000**
* *"What is the arrival grace period for morning check-in?"* → **30 minutes**
* *"How many days of annual leave do employees get?"* → **24 days**
* *"What is the password rotation period?"* → **90 days**

### 2. What-If Policy Impact Simulator
Test hypothetical scenarios with multi-clause verdicts:
* *"I want to work remotely for 2 days next week."*
* *"I received a gift worth Rs. 5,000 from a vendor. Can I keep it?"*
* *"I want to claim Rs. 30,000 for my AWS certification exam and prep courses."*
* *"I have a headache and want to take 1 day of sick leave without a medical certificate."*

### 3. Running Automated Tests
To run all 22 integration and unit tests:
```bash
# In Docker
docker exec -it policy_ledger_app pytest tests/ -v

# Locally
pytest tests/ -v
```

---

## 🛑 Turning Off / Shutting Down

### 1. Stop Containers (Preserves Database Data)
```bash
docker compose down
```

### 2. Stop Containers & Delete Volumes (Complete Fresh Reset)
```bash
docker compose down -v
```

---

## 🌐 Option C: Production Docker Stack

For full production deployment with PostgreSQL database, Nginx reverse proxy, and resource limits:

```bash
# 1. Start production stack
docker compose -f docker-compose.prod.yml up -d --build

# 2. Seed database
docker exec -it policy_ledger_web python seed.py

# 3. Access production server
http://<your-server-ip-or-domain>

# 4. Stop production stack
docker compose -f docker-compose.prod.yml down
```
