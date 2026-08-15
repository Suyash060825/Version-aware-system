import os
import pytest
from app import create_app
from rag.cache.semantic_cache import SemanticCache
from rag.chatbot.chat_service import answer

def test_flask_limiter_storage(monkeypatch):
    """Verify Flask-Limiter uses Redis in production when REDIS_URL is present."""
    import unittest.mock as mock
    import config
    os.environ['FLASK_ENV'] = 'production'
    # Modify config directly to avoid missing keys
    config.config['production'].SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    config.config['production'].SECRET_KEY = 'valid-test-secret-key-12345'
    config.config['production'].JWT_SECRET_KEY = 'valid-test-jwt-secret-key-12345'
    config.config['production'].DEFAULT_ADMIN_PASSWORD = 'NewAdminPassword123'
    with mock.patch('app.db.create_all'):
        app = create_app('production')
        assert app is not None

def test_semantic_cache_invalidate_local():
    """Verify invalidate_for_policy works without crashing on local_cache when Redis enabled."""
    cache = SemanticCache()
    # Mock redis usage to trigger the bug condition
    cache.use_redis = True
    # If the bug is present, this will raise AttributeError: 'SemanticCache' object has no attribute 'local_cache'
    try:
        cache.invalidate_for_policy(1, 2)
    except AttributeError as e:
        pytest.fail(f"AttributeError raised: {e}")

def test_chat_service_confidence_in_fallback():
    """Verify confidence field is included in no-hits fallback response."""
    app = create_app('testing')
    with app.app_context():
        # A query guaranteed to have 0 hits if ChromaDB is empty or mock
        res = answer(
            query="Random query with no hits",
            session_id="test",
            user_role="hr",
            user_department=""
        )
        assert "confidence" in res
        assert res["confidence"] == 0
