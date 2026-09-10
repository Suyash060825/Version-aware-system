# Veritas: Version-Aware Enterprise Policy Intelligence

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/framework-Flask_3.1-black.svg)](https://palletsprojects.com/p/flask/)
[![Docker Compose](https://img.shields.io/badge/container-Docker_Compose-2496ED.svg)](https://www.docker.com/)
[![Vector DB](https://img.shields.io/badge/vector_db-ChromaDB_|_FAISS_HNSW-purple.svg)](https://github.com/chroma-core/chroma)
[![Tests](https://img.shields.io/badge/tests-41%2F41_passing-success.svg)](pytest.ini)
[![Audit](https://img.shields.io/badge/view_audit-69%2F69_clean-brightgreen.svg)](scripts/audit_all_views.py)
[![IPR Status](https://img.shields.io/badge/IPR-Audit_Ready_|_Patent_Pending-orange.svg)](Version_Aware_Ieee.pdf)

**Veritas** is an enterprise-grade, version-aware policy intelligence and governance platform designed for high-compliance corporate environments. It resolves temporal drift, contradictory governance clauses, and stale AI answers through **Incremental Knowledge Compilation**, **Continuous Cross-Policy Contradiction Detection**, **Blast Radius Simulation**, and **Multi-Tier Adaptive Hybrid Retrieval**.

---

## 🏛️ Intellectual Property & Novel Claims Disclosure (IPR)

For evaluation and review by the intellectual property assessment team, the primary novel claims and their corresponding source code modules are documented below:

| Innovation Claim | Description | Core Implementation Files |
| :--- | :--- | :--- |
| **1. Multi-Stage Incremental Knowledge Compiler** | Autonomous 7-stage compilation transforming raw policy revisions into structurally segmented chunks, deterministic numerical facts, and pre-validated canonical Q&A pairs. | [`rag/compiler.py`](rag/compiler.py), [`rag/chunking.py`](rag/chunking.py), [`tasks.py`](tasks.py) |
| **2. Continuous Cross-Policy Contradiction Radar** | High-throughput semantic and NLI contradiction detection across divergent departmental policies, flagging clashing clauses before publication. | [`policy_ai.py`](policy_ai.py), [`blueprints/admin.py`](blueprints/admin.py) |
| **3. Blast Radius & What-If Impact Simulator** | Deterministic graph and semantic simulation measuring the organizational fallout, affected departments, and compliance risk of proposed policy revisions. | [`whatif_ai.py`](whatif_ai.py), [`blueprints/whatif.py`](blueprints/whatif.py) |
| **4. Multi-Tier Adaptive Retrieval Engine** | Hierarchical retrieval router combining Tier-1 Semantic Cache (Redis), Tier-2 FAISS HNSW Canonical QA fast-path, and Tier-3 ChromaDB dense + BM25 sparse RRF fusion reranked by Cross-Encoder. | [`rag/query_engine.py`](rag/query_engine.py), [`rag/dense_store.py`](rag/dense_store.py), [`rag/bm25_indexer.py`](rag/bm25_indexer.py) |
| **5. Evidence-Safe Grounded Verification & Ledger** | Zero-hallucination policy answers verified with NLI entailment scores, slide-over interactive drawer citations, and tamper-evident audit logging across 47 relational tables. | [`models.py`](models.py), [`blueprints/chat.py`](blueprints/chat.py), [`blueprints/audit.py`](blueprints/audit.py) |

---

## 📐 System Architecture

```
                                   [ Enterprise Policy Revision / Upload ]
                                                      │
                                                      ▼
                                ┌──────────────────────────────────────────┐
                                │   7-Stage Knowledge Compiler Pipeline    │
                                │   (Normalizer ➔ Chunker ➔ Fact Extractor │
                                │   ➔ QA Synthesizer ➔ Embedder ➔ Indexer) │
                                └─────────────────────┬────────────────────┘
                                                      │
                      ┌───────────────────────────────┼───────────────────────────────┐
                      ▼                               ▼                               ▼
              [ Persistent BM25 ]            [ ChromaDB Dense Store ]        [ FAISS HNSW Canonical QA ]
              Sparse Keyword Index           Contextual Late Chunking        Sub-Millisecond Cache & ANN
                      │                               │                               │
                      └───────────────────────┬───────┴───────────────────────────────┘
                                              │
                                              ▼
                              ┌───────────────────────────────┐
                              │   Multi-Tier Query Engine     │
                              │   - Tier 1: Semantic Cache    │
                              │   - Tier 2: Canonical Match   │
                              │   - Tier 3: Hybrid Dense/BM25 │
                              │   - TinyBERT Cross-Encoder    │
                              └───────────────┬───────────────┘
                                              │
                                              ▼
                               [ Version-Aware Grounded Answer ]
                               + NLI Entailment Verification
                               + Slide-Over Interactive Citations
```

---

## 📂 Repository Directory Structure

```text
Veritas/
├── app.py                     # Application factory, extensions, and lifecycle setup
├── wsgi.py                    # Production WSGI application gateway
├── config.py                  # Production & development environment settings
├── extensions.py              # Central Flask extensions (SQLAlchemy, Migrate, Limiter)
├── models.py                  # 47 relational database models (policies, versions, audits, MOM)
├── seed.py                    # Deterministic production database and index seeder
├── tasks.py                   # Celery asynchronous task definitions (compilation, audits)
├── benchmark.py               # RAG latency and retrieval benchmark suite
├── digest_engine.py           # Daily executive governance digest generator
├── meeting_ai.py              # AI executive meeting & minutes (MOM) engine
├── policy_ai.py               # Contradiction radar and policy intelligence algorithms
├── whatif_ai.py               # Blast radius and what-if simulation engine
├── workflow_engine.py         # Multi-step policy approval and lifecycle state machine
├── utils.py                   # Utility functions (date formatting, metrics, tokens)
├── Dockerfile                 # Hardened container image specification
├── docker-compose.yml         # Multi-service stack (Nginx, Web, Celery, Postgres, Redis, Ollama)
├── requirements.txt           # Audited, pinned Python dependencies
├── .env.example               # Secure environment variables template
├── pytest.ini                 # Pytest configuration
├── STARTUP.md                 # Step-by-step evaluator and developer startup guide
├── Version_Aware_Ieee.pdf     # Full IEEE publication manuscript & mathematical proofs
├── Version_Aware_Ieee.tex     # LaTeX source of research paper
│
├── blueprints/                # Modular Flask route blueprints (12 functional areas)
│   ├── admin.py               # System administration, governance, analytics, RBAC
│   ├── api.py                 # RESTful APIs for programmatic integration
│   ├── audit.py               # Forensic audit center, timelines, security logs
│   ├── auth.py                # Authentication, sessions, role authorization
│   ├── chat.py                # Grounded AI search with slide-over citations
│   ├── compliance.py          # Departmental compliance tracking, certificates, quizzes
│   ├── dashboard.py           # Enterprise and employee KPI dashboards
│   ├── meetings.py            # Board meetings, minutes, action items tracking
│   ├── notifications.py       # Notification center and alert dispatch
│   ├── policies.py            # Policy catalog, revision diffs, digital sign-offs
│   ├── search.py              # Boolean search, filters, saved queries
│   └── whatif.py              # Scenario modeling and blast radius UI
│
├── rag/                       # Retrieval-Augmented Generation & Compiler Subsystem
│   ├── chunking.py            # Structure-aware heading-preserving chunker
│   ├── compiler.py            # 7-stage policy compilation orchestrator
│   ├── dense_store.py         # ChromaDB client & vector collection manager
│   ├── bm25_indexer.py        # Persistent sparse BM25 indexer
│   ├── faiss_indexer.py       # FAISS HNSW fast-path indexer
│   ├── query_engine.py        # Multi-tier hybrid retrieval coordinator
│   ├── reranker.py            # Cross-encoder semantic reranking
│   └── normalizer.py          # Document cleaning and SHA-256 fingerprinting
│
├── scripts/                   # Automated validation and verification tools
│   ├── audit_all_views.py     # Comprehensive health audit covering all 69 platform views
│   └── test_policy_creation_lifecycle.py # End-to-end policy creation & auto-compilation test
│
├── tests/                     # Unit and integration test suites (41 tests)
│   ├── integration/           # Multi-component compiler and query engine tests
│   ├── test_rbac.py           # Role-based access control security tests
│   ├── test_rag_pipeline.py   # RAG pipeline accuracy tests
│   ├── test_whatif_ai.py      # What-if simulator verification tests
│   └── test_hardening_regression.py # Zero-defect edge-case and regression tests
│
├── templates/                 # Production Jinja2 user interfaces (responsive dark/light)
├── documentation/             # Comprehensive technical, architectural, and security audits
└── results/                   # Experimental benchmark records and latency evaluations
```

---

## 🚀 Quick Start (Docker - Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/Suyash060825/Veritas.git
cd Veritas

# 2. Launch the containerized stack
docker compose up -d --build

# 3. Initialize & seed all 47 relational database tables and compile indexes
docker compose exec -T web python seed.py

# 4. Access the platform
# Web Interface: http://localhost:8080
```

### Pre-Configured Evaluation Credentials

| Role | Email | Password | Access Scope |
| :--- | :--- | :--- | :--- |
| **System Admin** | `admin@company.com` | `Admin@6997d0cd111c34a0` | Full administrative control, knowledge graph, analytics |
| **HR Director** | `hr@company.com` | `HR@1234` | Policy authoring, approvals, contradiction resolution |
| **Employee** | `employee@company.com` | `Emp@1234` | AI search, interactive citation drawers, acknowledgements |

---

## 💻 Local Standalone Execution (Native Python)

For testing or development without Docker containers:

```bash
# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Seed SQLite database and build baseline vector indexes
python seed.py

# 4. Run the Flask application
python app.py
# Open: http://localhost:5000
```

---

## 🧪 Verification & Audit Protocol

The platform includes an automated testing and auditing suite ensuring zero runtime defects:

```bash
# 1. Execute the comprehensive unit & regression test suite (41 passed, 0 failures)
pytest

# 2. Execute the full platform view audit across all 69 administrator and employee routes
python scripts/audit_all_views.py

# 3. Verify all 5 policy creation pathways and real-time dashboard metric compilation
python scripts/test_policy_creation_lifecycle.py
```

---

## 🔬 Scientific & Technical Publications

The underlying mathematical foundations, algorithmic proofs, and empirical benchmark evaluations of the Veritas system are published in the accompanying research paper:

- **IEEE Manuscript**: [`Version_Aware_Ieee.pdf`](Version_Aware_Ieee.pdf)
- **LaTeX Source Code**: [`Version_Aware_Ieee.tex`](Version_Aware_Ieee.tex)
- **Detailed Audit Log**: [`documentation/final-audit.md`](documentation/final-audit.md)
- **System Startup Guide**: [`STARTUP.md`](STARTUP.md)

---

## 🛡️ License & Intellectual Property

Copyright © 2026 Suyash Pradhan. All rights reserved.  
This software and its proprietary algorithms (Knowledge Compiler, Contradiction Radar, Blast Radius Simulator, and Multi-Tier Hybrid Retrieval) are submitted for Intellectual Property Rights (IPR) and patent filing. Unauthorized copying, distribution, or decompilation is strictly prohibited.
