# System Architecture Map

## Directory Structure
```text
.
├── alembic/ (Database Migrations)
├── blueprints/ (Flask Blueprints / Routes)
├── data/ (Local Storage & Vector DB)
├── docs/ (Documentation)
├── eval/ (Evaluation Scripts & Data)
├── instance/ (Flask Instance Folder)
├── nginx/ (Web Server Config)
├── rag/ (Retrieval-Augmented Generation & AI Services)
├── scripts/ (Utility & Background Scripts)
├── templates/ (HTML Jinja Templates)
├── tests/ (Test Suite)
├── app.py (Main Application Entry Point)
├── config.py (Configuration Settings)
├── models.py (SQLAlchemy Database Models)
├── utils.py (Utility Functions)
├── whatif_ai.py (What-If Scenario Simulation Engine)
├── policy_ai.py (Policy AI Engine)
├── meeting_ai.py (Meeting AI Engine)
├── workflow_engine.py (Workflow Engine)
├── digest_engine.py (Digest Engine)
└── seed.py (Database Seeding)
```

## System Overview & Dependency Flow

The system is a modular Flask application designed for policy management and AI-driven compliance checks. It separates concerns across web routing, relational data, vector search, and AI processing.

### Key Modules and Responsibilities
- **App & Blueprints (`app.py`, `blueprints/`)**: Handles web routing, authentication, and HTTP request lifecycles.
- **Relational Data (`models.py`, `alembic/`)**: SQLAlchemy models storing users, policies, versioning, roles (RBAC), and workflows.
- **RAG Pipeline (`rag/`)**: Core AI primitives including document chunking, embedding, ChromaDB vector storage, reranking, and LLM provider abstractions.
- **What-If AI Engine (`whatif_ai.py`)**: Specialized compliance simulator. It translates user scenarios into structured verdicts (compliant/not_compliant/depends) using retrieved policy chunks.
- **Policy AI Engine (`policy_ai.py`)**: General conversational AI and document QA.
- **Workflow Engine (`workflow_engine.py`)**: Handles the state machine for policy approvals (Draft -> Review -> Published).

### Core Data Flow
1. **User Request**: A user submits a query or scenario via the UI.
2. **Web Layer**: A blueprint route authenticates and sanitizes the request.
3. **Embedding & Retrieval**: The query is embedded (via `rag/embeddings/`) and a similarity search is performed against ChromaDB (`data/chroma/`), with metadata filtering by user department/role.
4. **Reranking**: The retrieved chunks are reranked to prioritize relevance.
5. **LLM Generation**: Top chunks and the system prompt are passed to the LLM Provider. For `whatif_ai.py`, it enforces JSON structured output for compliance verdicts.
6. **Response Formulation**: The result, along with citations and confidence scores, is returned to the UI.

### External Dependencies and Services
- **Database Backend**: SQLite (development/testing) or PostgreSQL (production) via SQLAlchemy.
- **Vector Database**: ChromaDB (local persistence).
- **LLM Providers**: Modular integration (e.g., Gemini, vLLM, OpenAI) via `rag/llm_provider.py`.
- **Background Tasks**: Managed via ad-hoc scripts or scheduling mechanisms (e.g., `tasks.py`, `digest_engine.py`).
