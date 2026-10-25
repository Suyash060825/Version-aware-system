import pytest
from datetime import date
from unittest.mock import patch
from app import create_app
from models import db, User, UserRole, Policy, PolicyVersion, PolicyChunkV2, PolicyStatus, ConfidentialityLevel
from rag.engine.query_engine import QueryEngine
from rag.authorization.evidence_filter import revoke_user_permission, get_user_auth_epoch
from rag.cache.semantic_cache import get_cache

def test_immediate_permission_revocation_and_cache_isolation():
    app = create_app("testing")
    with app.app_context():
        db.create_all()

        user_a = User(name="User A", email="usera_revoc@test.com", password_hash="hash", role=UserRole.MANAGER, department_id=2)
        db.session.add(user_a)
        db.session.commit()

        pol = Policy(policy_id="POL-REVOC-01", title="Executive Bonus Formula", confidentiality=ConfidentialityLevel.CONFIDENTIAL, department_id=2, author_id=user_a.id, status=PolicyStatus.ACTIVE)
        db.session.add(pol)
        db.session.commit()
        ver = PolicyVersion(policy_id=pol.id, version_num=1.0, version_label="v1.0", is_active=True, content="Executive bonus target is 40% of base salary.", created_by_id=user_a.id)
        db.session.add(ver)
        db.session.commit()
        chk = PolicyChunkV2(chunk_id="chk-revoc-1", policy_id=pol.id, version_id=ver.id, text="Executive bonus target is 40% of base salary.", section_path="Section 1")
        db.session.add(chk)
        db.session.commit()

        # Step 1: User A has manager permissions in Dept 2 initially
        user_a.department_id = 2
        user_a.role = UserRole.MANAGER
        db.session.commit()

        engine = QueryEngine()
        cache = get_cache()
        cache.clear()

        query = "What is the executive bonus target in Executive Bonus Formula?"

        mock_chunk = {
            "chunk_id": "chk-revoc-1",
            "policy_id": pol.id,
            "version_id": ver.id,
            "text": "Executive bonus target is 40% of base salary.",
            "title": pol.title,
            "version": "1.0",
            "confidentiality": "confidential",
            "department_id": 2
        }

        with patch.object(engine.hybrid_retriever, "search", return_value=[mock_chunk]):
            # Step 2: Query policy, populating caches
            res1 = engine.answer(query, user=user_a)
            assert not res1.abstained
            assert "40%" in res1.answer

            # Verify that repeating query hits cache
            res_cache = engine.answer(query, user=user_a)
            assert not res_cache.abstained
            assert res_cache.route == "CACHE_HIT"

            # Step 3: Administrator revokes User A's permission immediately
            user_a.department_id = 1
            user_a.role = UserRole.EMPLOYEE
            db.session.commit()

            new_epoch = revoke_user_permission(user_a.id)
            assert new_epoch > 1

            # Step 4: User A immediately repeats the same query
            res2 = engine.answer(query, user=user_a)

            # Step 5: Request is denied / abstained, cannot be served from stale cache
            assert res2.abstained or "not authorized" in res2.answer.lower() or "could not find sufficient" in res2.answer.lower()
            assert res2.route != "CACHE_HIT"

def test_redis_unavailability_failsafe_revocation():
    """Verify that even when Redis is down or times out, local epoch and cache invalidation succeed fail-safe."""
    with patch("redis.Redis.from_url") as mock_redis:
        mock_redis.side_effect = Exception("Redis connection refused")
        user_id = 9999
        initial_epoch = get_user_auth_epoch(user_id)
        new_epoch = revoke_user_permission(user_id)
        assert new_epoch == initial_epoch + 1
        assert get_user_auth_epoch(user_id) == new_epoch
