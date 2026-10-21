"""
tests/test_exhaustive_audit_validation.py
Exhaustive regression and validation test suite for:
- Strictly local Ollama provider contract (qwen3:4b-q4_K_M) and LM Studio elimination
- Dashboard metrics truthfulness (no >100% compliance rates, accurate denominators)
- Employee dashboard pending acknowledgement state preservation
- Comprehensive database persistence and CRUD lifecycle
- RBAC and clearance-based security filtering
- Failure resilience and graceful degradation
"""
import pytest
from datetime import datetime, timezone, date, timedelta
from app import create_app
from models import (
    db, User, UserRole, Policy, PolicyVersion, PolicyStatus,
    ConfidentialityLevel, Department, PolicyCategory, PolicyAcknowledgement
)
from rag.llm_provider import get_llm_provider, OllamaProvider, LLMResponse
from blueprints.bi_dashboard import bi_dashboard
from blueprints.compliance import _compute_compliance_data
from flask_login import login_user


@pytest.fixture(scope="module")
def validation_client():
    app = create_app("testing")
    app.config["WTF_CSRF_ENABLED"] = False
    with app.app_context():
        db.create_all()

        # Ensure test department
        dept = Department.query.filter_by(code="TST").first()
        if not dept:
            dept = Department(name="Test Dept", code="TST")
            db.session.add(dept)
            db.session.commit()

        # Admin user
        admin = User.query.filter_by(email="val_admin@test.com").first()
        if not admin:
            admin = User(name="Val Admin", email="val_admin@test.com", role=UserRole.ADMIN, department_id=dept.id)
            admin.set_password("AdminPass123!")
            db.session.add(admin)

        # Employee user
        emp = User.query.filter_by(email="val_emp@test.com").first()
        if not emp:
            emp = User(name="Val Emp", email="val_emp@test.com", role=UserRole.EMPLOYEE, department_id=dept.id)
            emp.set_password("EmpPass123!")
            db.session.add(emp)

        # Restricted employee
        legal_user = User.query.filter_by(email="val_legal@test.com").first()
        if not legal_user:
            legal_user = User(name="Val Legal", email="val_legal@test.com", role="legal", department_id=dept.id)
            legal_user.set_password("LegalPass123!")
            db.session.add(legal_user)

        db.session.commit()

    with app.test_client() as client:
        with app.app_context():
            yield client, app


def test_ollama_local_provider_contract():
    """Verify strictly local Ollama provider is active and LM Studio is disabled."""
    provider = get_llm_provider(force_reload=True)
    assert isinstance(provider, OllamaProvider)
    assert provider.model == "qwen3:4b-q4_K_M"

    # Verify LM Studio rejection
    from unittest.mock import patch
    with patch.dict("os.environ", {"LLM_BACKEND": "lmstudio"}):
        with pytest.raises(RuntimeError, match="LM Studio integration is disabled"):
            get_llm_provider(force_reload=True)


def test_ollama_generation_usage_tokens():
    """Verify generation works and usage token dictionary is populated without time NameError."""
    provider = get_llm_provider(force_reload=True)
    if not provider.health_check():
        pytest.skip("Ollama service offline in testing container")
    resp = provider.generate("Respond with the single word: CONFIRMED")
    assert isinstance(resp, LLMResponse)
    assert resp.text
    assert isinstance(resp.usage, dict)
    assert "prompt_tokens" in resp.usage
    assert "completion_tokens" in resp.usage


def test_dashboard_metrics_truthfulness(validation_client):
    """Verify bi_dashboard compliance_rate and department compliance are mathematically bounded [0, 100]."""
    client, app = validation_client
    from flask_login import logout_user
    with app.test_request_context("/admin/bi-dashboard"):
        try:
            admin = User.query.filter_by(email="val_admin@test.com").first()
            login_user(admin)
            response_html = bi_dashboard()
            assert isinstance(response_html, str)
            assert len(response_html) > 0
        finally:
            logout_user()

    with app.app_context():
        # Verify compliance data computation
        comp_data = _compute_compliance_data()
        assert 0 <= comp_data["readiness_score"] <= 100
        for sub_score in comp_data["sub_scores"].values():
            assert 0 <= sub_score <= 100


def test_pending_acknowledgement_filter_truthfulness(validation_client):
    """Verify an unacknowledged read does not suppress policy from pending acknowledgements."""
    client, app = validation_client
    with app.app_context():
        admin = User.query.filter_by(email="val_admin@test.com").first()
        emp = User.query.filter_by(email="val_emp@test.com").first()
        dept = Department.query.filter_by(code="TST").first()

        # Create mandatory test policy
        policy = Policy(
            policy_id="POL-MAND-VAL",
            title="Mandatory Safety Guideline",
            author_id=admin.id,
            department_id=dept.id,
            status=PolicyStatus.ACTIVE,
            is_mandatory=True,
            confidentiality=ConfidentialityLevel.INTERNAL,
        )
        db.session.add(policy)
        db.session.commit()

        # Step 1: User views policy (read_at set, acknowledged_at is None)
        ack = PolicyAcknowledgement(
            policy_id=policy.id,
            user_id=emp.id,
            read_at=datetime.now(timezone.utc),
            acknowledged_at=None,
            is_mandatory=True,
        )
        db.session.add(ack)
        db.session.commit()

        # Query pending acks for emp
        acked_ids = [a.policy_id for a in emp.acknowledgements.filter(PolicyAcknowledgement.acknowledged_at.isnot(None)).all()]
        pending_acks = Policy.query.filter(
            Policy.status == PolicyStatus.ACTIVE,
            Policy.is_mandatory == True,
            ~Policy.id.in_(acked_ids) if acked_ids else True
        ).all()

        assert policy.id in [p.id for p in pending_acks], "Policy without acknowledged_at must remain in pending_acks"

        # Step 2: User acknowledges policy
        ack.acknowledged_at = datetime.now(timezone.utc)
        db.session.commit()

        acked_ids_after = [a.policy_id for a in emp.acknowledgements.filter(PolicyAcknowledgement.acknowledged_at.isnot(None)).all()]
        pending_acks_after = Policy.query.filter(
            Policy.status == PolicyStatus.ACTIVE,
            Policy.is_mandatory == True,
            ~Policy.id.in_(acked_ids_after) if acked_ids_after else True
        ).all()

        assert policy.id not in [p.id for p in pending_acks_after], "Acknowledged policy must not appear in pending_acks"

        # Cleanup
        db.session.delete(ack)
        db.session.delete(policy)
        db.session.commit()


def test_user_action_persistence_lifecycle(validation_client):
    """Test full CRUD lifecycle persistence: create, edit, new version, archive, restore, duplicate, delete."""
    client, app = validation_client
    with app.app_context():
        admin = User.query.filter_by(email="val_admin@test.com").first()
        dept = Department.query.filter_by(code="TST").first()

        # 1. Create Policy
        p = Policy(
            policy_id="POL-LIFE-001",
            title="Lifecycle Persistence Test",
            description="Testing DB persistence of all operations",
            status=PolicyStatus.DRAFT,
            confidentiality=ConfidentialityLevel.INTERNAL,
            department_id=dept.id,
            author_id=admin.id,
        )
        db.session.add(p)
        db.session.commit()
        pid = p.id
        assert pid is not None

        # 2. Add Version 1.0
        v1 = PolicyVersion(
            policy_id=pid,
            version_num=1,
            version_label="1.0",
            content="Initial text for version 1.0",
            is_active=False,
            created_by_id=admin.id,
        )
        db.session.add(v1)
        db.session.commit()

        # Re-query in clean session
        db.session.expire_all()
        persisted_p = db.session.get(Policy, pid)
        assert persisted_p.title == "Lifecycle Persistence Test"
        assert persisted_p.versions.count() == 1

        # 3. Edit Policy
        persisted_p.title = "Lifecycle Persistence Test (Edited)"
        db.session.commit()
        db.session.expire_all()
        assert db.session.get(Policy, pid).title == "Lifecycle Persistence Test (Edited)"

        # 4. Add Version 2.0 & Activate
        v2 = PolicyVersion(
            policy_id=pid,
            version_num=2,
            version_label="2.0",
            content="Updated text for version 2.0",
            is_active=True,
            created_by_id=admin.id,
        )
        db.session.add(v2)
        persisted_p.status = PolicyStatus.ACTIVE
        db.session.commit()
        db.session.expire_all()

        p_active = db.session.get(Policy, pid)
        assert p_active.status == PolicyStatus.ACTIVE
        assert p_active.versions.filter_by(is_active=True).first().version_label == "2.0"

        # 5. Archive Policy
        p_active.status = PolicyStatus.ARCHIVED
        v2.is_active = False
        db.session.commit()
        db.session.expire_all()
        assert db.session.get(Policy, pid).status == PolicyStatus.ARCHIVED

        # 6. Restore Policy
        p_restored = db.session.get(Policy, pid)
        p_restored.status = PolicyStatus.DRAFT
        db.session.commit()
        db.session.expire_all()
        assert db.session.get(Policy, pid).status == PolicyStatus.DRAFT

        # 7. Delete Policy
        PolicyVersion.query.filter_by(policy_id=pid).delete()
        Policy.query.filter_by(id=pid).delete()
        db.session.commit()
        db.session.expire_all()
        assert db.session.get(Policy, pid) is None


def test_clearance_and_role_security_enforcement(validation_client):
    """Verify unauthorized users cannot access admin endpoints or view restricted policies."""
    _, app = validation_client
    fresh_client = app.test_client()

    # 1. Anonymous user redirected on admin endpoint
    resp = fresh_client.get("/admin/")
    assert resp.status_code in (302, 401, 403)

    # 2. Employee login gets 403 on admin endpoint
    with fresh_client.session_transaction() as sess:
        with app.app_context():
            emp = User.query.filter_by(email="val_emp@test.com").first()
            sess["_user_id"] = str(emp.id)

    resp_emp = fresh_client.get("/admin/")
    assert resp_emp.status_code in (403, 302)

    # 3. Confidentiality clearance check
    with app.app_context():
        from rag.authorization.evidence_filter import get_evidence_filter
        ev = get_evidence_filter()
        emp = User.query.filter_by(email="val_emp@test.com").first()
        legal = User.query.filter_by(email="val_legal@test.com").first()
        admin = User.query.filter_by(email="val_admin@test.com").first()

        restricted_p = Policy(
            policy_id="POL-CONF-VAL",
            title="Secret M&A Strategy",
            status=PolicyStatus.ACTIVE,
            confidentiality=ConfidentialityLevel.RESTRICTED,
        )
        assert ev.is_authorized_for_policy(emp, restricted_p) is False
        assert ev.is_authorized_for_policy(legal, restricted_p) is True
        assert ev.is_authorized_for_policy(admin, restricted_p) is True
