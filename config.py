"""
config.py
Authoritative centralized configuration for Veritas / Policy Ledger v2.
Single source of truth for Flask web, Celery worker, RAG retrieval engine, AI providers, and evaluation.
"""
import os
import re
from datetime import timedelta
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # --- Core Application ---
    SECRET_KEY = os.environ.get("SECRET_KEY")
    DEBUG = False
    TESTING = False
    APP_NAME = os.environ.get("APP_NAME", "Policy Ledger")
    COMPANY_NAME = os.environ.get("COMPANY_NAME", "Acme Corporation")
    DEFAULT_ADMIN_EMAIL = os.environ.get("DEFAULT_ADMIN_EMAIL", "admin@company.com")
    DEFAULT_ADMIN_PASSWORD = os.environ.get("DEFAULT_ADMIN_PASSWORD")

    # --- RAG Guardrails ---
    PII_REDACTION_ENABLED = os.environ.get("PII_REDACTION_ENABLED", "True").lower() == "true"

    # --- Relational Database & pgvector ---
    _raw_db = os.environ.get("DATABASE_URL")
    if _raw_db and _raw_db.startswith("postgres://"):
        _raw_db = _raw_db.replace("postgres://", "postgresql://", 1)

    if _raw_db:
        SQLALCHEMY_DATABASE_URI = _raw_db
    else:
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'data', 'ledger.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Redis & Celery ---
    REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", REDIS_URL)
    CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", REDIS_URL)

    # --- Local AI & LLM Inference ---
    LLM_BACKEND = os.environ.get("LLM_BACKEND", "ollama")
    LOCAL_LLM_MODEL = os.environ.get("LOCAL_LLM_MODEL", os.environ.get("OLLAMA_MODEL", "qwen3:4b-q4_K_M"))
    OLLAMA_MODEL = LOCAL_LLM_MODEL
    LOCAL_LLM_BASE_URL = os.environ.get("LOCAL_LLM_BASE_URL", os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434")).rstrip("/")
    OLLAMA_BASE_URL = LOCAL_LLM_BASE_URL
    LLM_TIMEOUT = float(os.environ.get("LLM_TIMEOUT", "45.0"))
    LLM_MAX_NEW_TOKENS = int(os.environ.get("LLM_MAX_NEW_TOKENS", "512"))
    OLLAMA_NUM_CTX = int(os.environ.get("OLLAMA_NUM_CTX", "4096"))
    OLLAMA_KEEP_ALIVE = os.environ.get("OLLAMA_KEEP_ALIVE", "10m")
    OLLAMA_NUM_THREADS = int(os.environ.get("OLLAMA_NUM_THREADS", "0"))

    # --- Embeddings & Vector Indices ---
    EMBEDDING_ENGINE = os.environ.get("EMBEDDING_ENGINE", "fastembed")
    EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", os.environ.get("FASTEMBED_MODEL", "BAAI/bge-small-en-v1.5"))
    FASTEMBED_MODEL = EMBEDDING_MODEL
    EMBEDDING_DIMENSION = int(os.environ.get("EMBEDDING_DIMENSION", "384"))

    # --- Cross-Encoder Reranker ---
    RERANKER_ENGINE = os.environ.get("RERANKER_ENGINE", "flashrank")
    RERANKER_MODEL = os.environ.get("RERANKER_MODEL", os.environ.get("FLASHRANK_MODEL", "ms-marco-TinyBERT-L-2-v2"))
    FLASHRANK_MODEL = RERANKER_MODEL

    # --- Index Persistence Paths ---
    BM25_INDEX_PATH = os.environ.get("BM25_INDEX_PATH", os.path.join(BASE_DIR, "data", "bm25_index.pkl"))
    FAISS_INDEX_PATH = os.environ.get("FAISS_INDEX_PATH", os.path.join(BASE_DIR, "data", "canonical_qa_faiss.index"))
    CHROMA_PERSIST_DIR = os.environ.get("CHROMA_PERSIST_DIR", os.path.join(BASE_DIR, "data", "chroma"))

    # --- Caching & Retrieval Parameters ---
    SEMANTIC_CACHE_ENABLED = os.environ.get("SEMANTIC_CACHE_ENABLED", "true").lower() == "true"
    SEMANTIC_CACHE_THRESHOLD = float(os.environ.get("SEMANTIC_CACHE_THRESHOLD", "0.95"))
    CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", "3600"))
    DEFAULT_TOP_K = int(os.environ.get("DEFAULT_TOP_K", "5"))
    RERANK_TOP_K = int(os.environ.get("RERANK_TOP_K", "3"))

    # --- Deterministic Evaluation Constants ---
    EVAL_CORPUS_SEED = 42

    # --- JWT Authentication ---
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)

    # --- File Upload Limits ---
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "data", "uploads")
    MAX_CONTENT_LENGTH = 32 * 1024 * 1024  # 32 MB
    ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "md"}
    POLICY_IMPORT_EXTENSIONS = {"pdf", "docx", "xlsx", "xls", "txt", "md"}

    # --- Email Notifications ---
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "noreply@company.com")

    # --- MFA ---
    MFA_ISSUER = os.environ.get("MFA_ISSUER", "PolicyLedger")

    @classmethod
    def validate_configuration(cls) -> None:
        """Type and range validation for operational settings."""
        if cls.EMBEDDING_DIMENSION != 384 and "bge-small" in cls.EMBEDDING_MODEL:
            raise ValueError(f"EMBEDDING_DIMENSION {cls.EMBEDDING_DIMENSION} does not match bge-small model (expected 384)")
        if not (0.0 <= cls.SEMANTIC_CACHE_THRESHOLD <= 1.0):
            raise ValueError(f"SEMANTIC_CACHE_THRESHOLD must be between 0.0 and 1.0, got {cls.SEMANTIC_CACHE_THRESHOLD}")
        if cls.LLM_TIMEOUT <= 0:
            raise ValueError(f"LLM_TIMEOUT must be positive, got {cls.LLM_TIMEOUT}")
        if cls.MAX_CONTENT_LENGTH <= 0:
            raise ValueError(f"MAX_CONTENT_LENGTH must be positive, got {cls.MAX_CONTENT_LENGTH}")

    @classmethod
    def get_safe_diagnostics(cls) -> Dict[str, Any]:
        """Return non-sensitive configuration dictionary for observability and logging."""
        redacted_db = cls.SQLALCHEMY_DATABASE_URI
        if "@" in redacted_db:
            redacted_db = re.sub(r"://([^:]+):([^@]+)@", r"://\1:******@", redacted_db)
        return {
            "app_name": cls.APP_NAME,
            "database_uri": redacted_db,
            "redis_url": cls.REDIS_URL,
            "llm_backend": cls.LLM_BACKEND,
            "local_llm_model": cls.LOCAL_LLM_MODEL,
            "ollama_base_url": cls.OLLAMA_BASE_URL,
            "llm_timeout": cls.LLM_TIMEOUT,
            "embedding_engine": cls.EMBEDDING_ENGINE,
            "embedding_model": cls.EMBEDDING_MODEL,
            "embedding_dimension": cls.EMBEDDING_DIMENSION,
            "reranker_engine": cls.RERANKER_ENGINE,
            "reranker_model": cls.RERANKER_MODEL,
            "semantic_cache_enabled": cls.SEMANTIC_CACHE_ENABLED,
            "semantic_cache_threshold": cls.SEMANTIC_CACHE_THRESHOLD,
            "max_content_length_mb": cls.MAX_CONTENT_LENGTH / (1024 * 1024),
            "cloud_dependencies_disabled": True
        }


class DevelopmentConfig(Config):
    DEBUG = True
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-secret-key-12345")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-insecure-jwt-key-12345")
    DEFAULT_ADMIN_PASSWORD = os.environ.get("DEFAULT_ADMIN_PASSWORD", "DevAdmin#2026!")


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
    SESSION_COOKIE_SAMESITE = "Lax"

    @classmethod
    def validate_production_secrets(cls):
        secret = os.environ.get("SECRET_KEY", "")
        jwt_secret = os.environ.get("JWT_SECRET_KEY", "")
        admin_pw = os.environ.get("DEFAULT_ADMIN_PASSWORD", "")
        insecure_defaults = {
            "change-this-in-production-please",
            "dev-secret-key",
            "dev-insecure-secret-key-12345",
            "dev-insecure-jwt-key-12345",
            "Admin@1234",
            "DevAdmin#2026!",
            ""
        }
        if not secret or secret in insecure_defaults:
            raise ValueError("Insecure or missing SECRET_KEY in production environment. Set a strong SECRET_KEY.")
        if not jwt_secret or jwt_secret in insecure_defaults:
            raise ValueError("Insecure or missing JWT_SECRET_KEY in production environment. Set a strong JWT_SECRET_KEY.")
        if not admin_pw or admin_pw in insecure_defaults:
            raise ValueError("Insecure or missing DEFAULT_ADMIN_PASSWORD in production environment. Set a strong DEFAULT_ADMIN_PASSWORD.")


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SECRET_KEY = "testing-secret-key-12345"
    JWT_SECRET_KEY = "testing-jwt-key-12345"
    DEFAULT_ADMIN_PASSWORD = "TestingAdmin#2026!"
    REDIS_URL = "redis://redis:6379/1"
    BM25_INDEX_PATH = ":memory:"
    FAISS_INDEX_PATH = ":memory:"
    SEMANTIC_CACHE_ENABLED = False


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
