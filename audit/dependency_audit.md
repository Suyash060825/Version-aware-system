# Veritas Dependency & Package Integrity Audit

**Audit Date:** 2026-10-21  
**Scope:** Dependency manifests (`requirements.txt`), Docker container installed packages, Python 3.11 ABI compatibility, and imported package audit.  

---

## 1. Direct Dependency Manifest Inventory (`requirements.txt`)

| Package | Version Constraint | Category | Runtime Subsystem | Container Status | ABI / Native Constraints |
|---|---|---|---|---|---|
| **flask** | `>=3.0.0` | Core Web | Application Factory, Blueprints | Installed | Pure Python |
| **flask-sqlalchemy** | `>=3.1.0` | ORM | Relational Models, Transactions | Installed | Pure Python |
| **flask-login** | `>=0.6.3` | Auth | Session Management, User Loader | Installed | Pure Python |
| **flask-bcrypt** | `>=1.0.1` | Auth | Password Hashing (Blowfish) | Installed | Native C extension |
| **flask-wtf** | `>=1.2.1` | Forms / CSRF | Request Validation, CSRF Protection | Installed | Pure Python |
| **flask-jwt-extended** | `>=4.6.0` | Auth | REST API Token Validation | Installed | Pure Python |
| **flask-limiter** | `>=3.5.0` | Security | Rate Limiting (Redis backend) | Installed | Pure Python |
| **python-dotenv** | `>=1.0.1` | Config | `.env` Loading | Installed | Pure Python |
| **pyotp** | `>=2.9.0` | Auth | Time-Based One-Time Passwords (MFA)| Installed | Pure Python |
| **qrcode[pil]** | `>=7.4.0` | Auth | MFA QR Code Rendering | Installed | Pure Python / Pillow |
| **pillow** | `>=10.0.0` | Media | Image Processing | Installed | Native libjpeg/zlib |
| **python-dateutil** | `>=2.9.0` | Utilities | Temporal Arithmetic & Parsing | Installed | Pure Python |
| **sentence-transformers**| `>=3.0.0` | ML | PyTorch Cross-Encoder Verification | Installed | PyTorch (CPU wheel) |
| **chromadb** | `*` | Vector DB | Persistent Vector Store | Installed | Requires Python <= 3.12 (ABI3 Rust bindings) |
| **PyMuPDF** | `>=1.24.0` | Ingestion | PDF Parsing & Metadata Extraction | Installed | Native MuPDF C library |
| **pdfplumber** | `>=0.11.0` | Ingestion | Table Extraction from Documents | Installed | Pure Python |
| **python-docx** | `>=1.1.0` | Ingestion | Office Open XML Document Parsing | Installed | Pure Python |
| **openpyxl** | `>=3.1.0` | Ingestion | Excel Spreadsheet Parsing | Installed | Pure Python |
| **reportlab** | `>=4.0.0` | Export | PDF Generation & Export | Installed | Native C extension |
| **psycopg2-binary** | `>=2.9.9` | Database | PostgreSQL 16 Driver | Installed | Native libpq C bindings |
| **psycopg[binary]** | `>=3.1.18` | Database | Modern Async PostgreSQL 3 Driver | Installed | Native C extension |
| **alembic** | `>=1.13.0` | Database | Database Migrations | Installed | Pure Python |
| **celery** | `>=5.3.0` | Tasks | Asynchronous Task Queue | Installed | Pure Python |
| **redis** | `>=5.0.0` | Cache / Tasks | Redis 7 Client & Message Broker | Installed | Native hiredis optional |
| **prometheus-client** | `>=0.20.0` | Observability| Prometheus Metrics Export | Installed | Pure Python |
| **gunicorn** | `>=21.2.0` | Production WSGI| Production Web Worker Server | Installed | Pure Python |
| **rank-bm25** | `*` | Retrieval | Okapi BM25 Sparse Inverted Index | Installed | Pure Python |
| **requests** | `*` | HTTP Client | Ollama Local API Client | Installed | Pure Python |
| **matplotlib** | `*` | Analytics | Evaluation Plotting & Curves | Installed | Native freetype/png |
| **pandas** | `*` | Data Analysis| CSV Generation & Metric Tabulation | Installed | Native C / Cython |
| **fastembed** | `>=0.3.0` | Embeddings | BAAI/bge-small ONNX Inference | Installed | ONNX Runtime CPU |
| **flashrank** | `>=0.2.0` | Reranker | TinyBERT Cross-Encoder ONNX | Installed | ONNX Runtime CPU |
| **pgvector** | `>=0.2.5` | Vector DB | PostgreSQL Vector Extension Client| Installed | Native C extension |
| **faiss-cpu** | `>=1.8.0` | Vector DB | Canonical QA HNSW Dense Index | Installed | Native OpenMP / BLAS |
| **pytest** | `>=8.0.0` | Testing | Test Suite Execution | Installed | Test runner |

---

## 2. Issues Discovered & Remediation Actions

1. **Obsolete Cloud Dependency Removed:**
   - **Finding:** `openai>=1.51.0` was present in `requirements.txt`.
   - **Root Cause:** Artifact of early experimental prototype. Veritas mandates strict local inference (`qwen3:4b-q4_K_M` via Ollama).
   - **Action Taken:** Removed `openai` from `requirements.txt`. Removed deferred OpenRouter import in `rag/llm_provider.py`.
2. **Host vs Container Python Runtime Incompatibility:**
   - **Finding:** Host runs Python `3.14.6`. Executing ChromaDB or FAISS on the host causes `SIGSEGV` in `chromadb_rust_bindings.abi3.so` due to pre-release Python 3.14 C-API changes.
   - **Remediation:** Standardized container runtime on **Python 3.11.17** (`python:3.11-slim`). All unit tests, background tasks, and benchmarks execute exclusively inside the Docker container, resulting in zero segfaults.
3. **PyTorch CPU Pre-Installation Strategy:**
   - **Verified:** `Dockerfile` installs `--index-url https://download.pytorch.org/whl/cpu` prior to requirements installation, saving ~2.5 GB of unnecessary CUDA binaries while maintaining full CPU inference compatibility.
