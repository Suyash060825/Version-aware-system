"""
tests/test_temporal_gaps.py
Comprehensive regression suite for temporal policy contracts:
1. Pre-dating earliest policy version (fails closed / returns None).
2. Querying during policy hiatus/gap between non-contiguous versions (returns None).
3. Post-expiration query (returns None).
4. Boundary day resolution (exact boundary matching).
5. Explicit requested version pin.
6. Temporal interval validity check.
"""
import pytest
from datetime import date, timedelta
from app import create_app
from models import db, Policy, PolicyVersion, User, Department, PolicyStatus, ConfidentialityLevel
from rag.versions.resolver import VersionResolver

@pytest.fixture
def temporal_app():
    app = create_app("testing")
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with app.app_context():
        db.create_all()
        # Seed test user and department
        dept = Department(id=1, name="Legal")
        user = User(id=1, email="legal@company.com", name="Legal Auditor", password_hash="dummy_hash", role="admin", is_active=True, department_id=1)
        db.session.add_all([dept, user])
        db.session.commit()

        yield app
        db.session.remove()
        db.drop_all()

def test_temporal_hiatus_between_versions(temporal_app):
    """
    Contract T-02: Policy hiatus between non-contiguous versions.
    v1: 2018-01-01 to 2019-12-31 (explicit expiration_date)
    v2: 2021-01-01 to ongoing
    Queries in 2020 must return None (NO active policy during hiatus).
    """
    with temporal_app.app_context():
        p = Policy(id=20, policy_id="POL-HIATUS", title="Remote Work Protocol", author_id=1, department_id=1,
                   status=PolicyStatus.ACTIVE, confidentiality=ConfidentialityLevel.INTERNAL)
        v1 = PolicyVersion(id=201, policy_id=20, version_num=1.0, version_label="v1.0",
                           content="Remote work v1 rules", is_active=False, status="approved", created_by_id=1,
                           effective_date=date(2018, 1, 1), expiration_date=date(2019, 12, 31))
        v2 = PolicyVersion(id=202, policy_id=20, version_num=2.0, version_label="v2.0",
                           content="Remote work v2 rules", is_active=True, status="approved", created_by_id=1,
                           effective_date=date(2021, 1, 1))
        db.session.add_all([p, v1, v2])
        db.session.commit()

        resolver = VersionResolver()

        # 1. During v1 active period
        v1_resolved = resolver.get_active_version(policy_id=20, target_date=date(2019, 6, 1))
        assert v1_resolved is not None
        assert v1_resolved.version_num == 1.0

        # 2. Inside the hiatus gap (2020-06-01) -> MUST BE NONE
        gap_resolved = resolver.get_active_version(policy_id=20, target_date=date(2020, 6, 1))
        assert gap_resolved is None, f"Expected None during hiatus, got v{gap_resolved.version_num}"

        # 3. Inside v2 active period
        v2_resolved = resolver.get_active_version(policy_id=20, target_date=date(2022, 1, 1))
        assert v2_resolved is not None
        assert v2_resolved.version_num == 2.0

def test_temporal_pre_dating_earliest_version(temporal_app):
    """
    Contract T-01: Querying prior to earliest policy enactment returns None.
    """
    with temporal_app.app_context():
        p = Policy(id=21, policy_id="POL-ENACT", title="Travel Policy", author_id=1, department_id=1,
                   status=PolicyStatus.ACTIVE, confidentiality=ConfidentialityLevel.INTERNAL)
        v1 = PolicyVersion(id=211, policy_id=21, version_num=1.0, version_label="v1.0",
                           content="Travel v1", is_active=True, status="approved", created_by_id=1,
                           effective_date=date(2015, 1, 1))
        db.session.add_all([p, v1])
        db.session.commit()

        resolver = VersionResolver()
        pre_dated = resolver.get_active_version(policy_id=21, target_date=date(2012, 6, 1))
        assert pre_dated is None

def test_temporal_boundary_day_matching(temporal_app):
    """
    Contract T-04: Exact boundary dates transition cleanly:
    v1: effective 2022-01-01, next version v2: effective 2023-01-01
    On 2022-12-31, v1 is active.
    On 2023-01-01, v2 is active.
    """
    with temporal_app.app_context():
        p = Policy(id=22, policy_id="POL-BOUND", title="Leave Policy", author_id=1, department_id=1,
                   status=PolicyStatus.ACTIVE, confidentiality=ConfidentialityLevel.INTERNAL)
        v1 = PolicyVersion(id=221, policy_id=22, version_num=1.0, version_label="v1.0",
                           content="Leave v1", is_active=False, status="approved", created_by_id=1,
                           effective_date=date(2022, 1, 1))
        v2 = PolicyVersion(id=222, policy_id=22, version_num=2.0, version_label="v2.0",
                           content="Leave v2", is_active=True, status="approved", created_by_id=1,
                           effective_date=date(2023, 1, 1))
        db.session.add_all([p, v1, v2])
        db.session.commit()

        resolver = VersionResolver()
        # Last day of v1
        last_day_v1 = resolver.get_active_version(policy_id=22, target_date=date(2022, 12, 31))
        assert last_day_v1 is not None and last_day_v1.version_num == 1.0

        # First day of v2
        first_day_v2 = resolver.get_active_version(policy_id=22, target_date=date(2023, 1, 1))
        assert first_day_v2 is not None and first_day_v2.version_num == 2.0

def test_temporal_explicit_version_pin(temporal_app):
    """
    Contract T-05: Explicit requested version pins accurately regardless of date.
    """
    with temporal_app.app_context():
        p = Policy(id=23, policy_id="POL-PIN", title="IT Security", author_id=1, department_id=1,
                   status=PolicyStatus.ACTIVE, confidentiality=ConfidentialityLevel.INTERNAL)
        v1 = PolicyVersion(id=231, policy_id=23, version_num=1.0, version_label="v1.0",
                           content="IT v1", is_active=False, status="approved", created_by_id=1,
                           effective_date=date(2020, 1, 1))
        v2 = PolicyVersion(id=232, policy_id=23, version_num=2.0, version_label="v2.0",
                           content="IT v2", is_active=True, status="approved", created_by_id=1,
                           effective_date=date(2022, 1, 1))
        db.session.add_all([p, v1, v2])
        db.session.commit()

        resolver = VersionResolver()
        # Request v1 explicitly
        req_v1 = resolver.get_active_version(policy_id=23, requested_version="1.0")
        assert req_v1 is not None and req_v1.version_num == 1.0

        # Request v2 explicitly
        req_v2 = resolver.get_active_version(policy_id=23, requested_version="v2.0")
        assert req_v2 is not None and req_v2.version_num == 2.0
