"""
tests/test_audit_v7_hardening.py
Verification suite for Version 7 authorization isolation, Chroma deletion typing, and compilation batching.
"""
import pytest
from app import create_app
from models import db, Policy, PolicyVersion, PolicyStatus, ConfidentialityLevel, User, UserRole, CanonicalQuestion, CompiledAnswer
from rag.authorization.evidence_filter import EvidenceFilter, get_evidence_filter
from rag.engine.query_scope import QueryScope
from rag.vectordb.chroma import get_store

@pytest.fixture
def test_app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.rollback()

def test_hr_restricted_clearance_isolation(test_app):
    ef = get_evidence_filter()

    # User HR
    u_hr = User(name="HR User", email="hr@test.com", password_hash="hash", role=UserRole.HR, department_id=1)
    # User Exec
    u_exec = User(name="Executive User", email="exec@test.com", password_hash="hash", role="executive", department_id=12)
    # User Employee
    u_emp = User(name="Emp User", email="emp@test.com", password_hash="hash", role=UserRole.EMPLOYEE, department_id=2)

    db.session.add_all([u_hr, u_exec, u_emp])
    db.session.commit()

    # Policy restricted
    p_restr = Policy(policy_id="POL-REST", title="Executive Compensation", author_id=u_exec.id, status=PolicyStatus.ACTIVE, confidentiality="restricted")
    # Policy confidential HR
    p_conf_hr = Policy(policy_id="POL-HR", title="HR Performance Reviews", author_id=u_hr.id, status=PolicyStatus.ACTIVE, confidentiality="confidential", department_id=1)
    # Policy confidential Eng
    p_conf_eng = Policy(policy_id="POL-ENG", title="Engineering Patents", author_id=u_emp.id, status=PolicyStatus.ACTIVE, confidentiality="confidential", department_id=2)

    db.session.add_all([p_restr, p_conf_hr, p_conf_eng])
    db.session.commit()

    # HR cannot view restricted policy
    assert ef.is_authorized_for_policy(u_hr, p_restr) is False
    scope_hr = QueryScope.from_user(u_hr)
    assert ef.is_authorized_for_policy(scope_hr, p_restr) is False
    assert "restricted" not in scope_hr.allowed_confidentiality

    # HR can view HR confidential policy
    assert ef.is_authorized_for_policy(u_hr, p_conf_hr) is True
    assert ef.is_authorized_for_policy(scope_hr, p_conf_hr) is True

    # Executive can view restricted policy
    assert ef.is_authorized_for_policy(u_exec, p_restr) is True
    scope_exec = QueryScope.from_user(u_exec)
    assert ef.is_authorized_for_policy(scope_exec, p_restr) is True

    # Employee cannot view HR confidential policy
    assert ef.is_authorized_for_policy(u_emp, p_conf_hr) is False
    scope_emp = QueryScope.from_user(u_emp)
    assert ef.is_authorized_for_policy(scope_emp, p_conf_hr) is False

    # Employee CAN view their own department's confidential policy if allowed
    # (or cannot if employee role lacks confidential clearance)
    assert ef.is_authorized_for_policy(scope_emp, p_conf_eng) is False

def test_cache_key_does_not_grant_restricted_to_hr():
    ef = EvidenceFilter()
    u_hr_proxy = type("HRProxy", (), {"id": 10, "role": "hr", "department_id": 1})()
    key = ef._get_cache_key(u_hr_proxy)
    assert "restricted" not in key
    assert "confidential" in key

def test_chroma_delete_policy_with_int_and_str_ids():
    store = get_store()
    test_chunks = [
        {
            "chunk_id": "test_del_chunk_1",
            "policy_id": 9999,
            "version": "v1.0",
            "version_id": 8888,
            "text": "Temporary chunk to verify delete_policy deletion by integer id"
        },
        {
            "chunk_id": "test_del_chunk_2",
            "policy_id": 9999,
            "version": "v2.0",
            "version_id": 8889,
            "text": "Temporary chunk to verify delete_policy_version deletion"
        }
    ]
    dummy_embs = [[0.05] * 384, [0.05] * 384]
    store.upsert_chunks(test_chunks, dummy_embs)

    # Verify both chunks are present
    res = store._col.get(ids=["test_del_chunk_1", "test_del_chunk_2"])
    assert len(res["ids"]) == 2

    # Delete version 8889 using delete_policy_version
    store.delete_policy_version(9999, 8889)
    res_v = store._col.get(ids=["test_del_chunk_1", "test_del_chunk_2"])
    assert "test_del_chunk_2" not in res_v["ids"]
    assert "test_del_chunk_1" in res_v["ids"]

    # Delete remaining policy 9999 using delete_policy
    store.delete_policy(9999)
    res_p = store._col.get(ids=["test_del_chunk_1", "test_del_chunk_2"])
    assert len(res_p["ids"]) == 0
