"""
tests/test_repo_consistency_repair.py
Regression tests for repository consistency, dependency integrity, configuration centralization, and safe runtime boundaries.
"""
import pytest
from config import Config, DevelopmentConfig, ProductionConfig, TestingConfig
from app import create_app
from models import db, User, Policy, PolicyVersion, UserRole


def test_config_validation_rules():
    """Verify Config.validate_configuration detects invalid operational parameters."""
    Config.validate_configuration()

    # Invalid embedding dimension
    original_dim = Config.EMBEDDING_DIMENSION
    try:
        Config.EMBEDDING_DIMENSION = 512
        with pytest.raises(ValueError, match="does not match bge-small"):
            Config.validate_configuration()
    finally:
        Config.EMBEDDING_DIMENSION = original_dim

    # Invalid cache threshold
    original_thresh = Config.SEMANTIC_CACHE_THRESHOLD
    try:
        Config.SEMANTIC_CACHE_THRESHOLD = 1.5
        with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
            Config.validate_configuration()
    finally:
        Config.SEMANTIC_CACHE_THRESHOLD = original_thresh


def test_safe_diagnostics_redacts_credentials():
    """Verify get_safe_diagnostics redacts secrets from database URLs."""
    diag = Config.get_safe_diagnostics()
    assert "database_uri" in diag
    assert "postgres:******@" in diag["database_uri"] or "sqlite" in diag["database_uri"]
    assert diag["embedding_dimension"] == 384
    assert diag["cloud_dependencies_disabled"] is True


def test_cloud_llm_provider_refusal():
    """Verify external cloud LLM providers are disabled and raise security exceptions."""
    from rag.llm_provider import GeminiProvider
    provider = GeminiProvider()
    with pytest.raises(RuntimeError, match="External cloud LLM inference APIs"):
        provider.generate("test prompt")


def test_celery_broker_centralized_configuration():
    """Verify Celery task maker uses centralized Config.REDIS_URL."""
    from tasks import make_celery
    test_celery = make_celery("test_worker")
    assert test_celery.conf.broker_url == Config.REDIS_URL
    assert test_celery.conf.result_backend == Config.REDIS_URL


def test_chroma_safe_collection_retrieval():
    """Verify Chroma vector store loads collection safely without rust metadata corruption."""
    from rag.vectordb.chroma import get_store
    store = get_store()
    assert store._col is not None
    assert store.embedding_dimension == 384
    count = store._col.count()
    assert isinstance(count, int)


def test_safe_anonymous_user_attributes():
    """Verify SafeAnonymousUser returns safe non-privileged defaults."""
    app = create_app("testing")
    with app.test_request_context():
        from flask_login import current_user
        assert current_user.is_authenticated is False
        assert current_user.can_manage_policies() is False
        assert current_user.is_admin() is False
        assert current_user.clearance == "public_only"
